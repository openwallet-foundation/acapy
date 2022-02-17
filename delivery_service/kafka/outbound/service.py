"""Kafka Outbound Delivery Service."""
import aiohttp
import asyncio
import logging
import msgpack
import sys
import urllib

from aiokafka import (
    AIOKafkaConsumer,
    ConsumerRebalanceListener,
    AIOKafkaProducer,
    TopicPartition,
    OffsetAndMetadata,
)
from aiokafka.errors import OffsetOutOfRangeError
from configargparse import ArgumentParser
from time import time
from uuid import uuid4

logging.basicConfig(
    format="%(asctime)s | %(levelname)s: %(message)s",
    level=logging.INFO,
)


class RebalanceListener(ConsumerRebalanceListener):
    """Listener to control actions before and after rebalance."""

    def __init__(self, consumer: AIOKafkaConsumer):
        """Initialize RebalanceListener."""
        self.consumer = consumer
        self.state = {}

    async def on_partitions_revoked(self, revoked):
        """Triggered on partitions revocation."""
        for tp in revoked:
            offset = self.state.get(tp)
            if offset and isinstance(offset, int):
                await self.consumer.commit({tp: OffsetAndMetadata(offset, "")})

    async def on_partitions_assigned(self, assigned):
        """Triggered on partitions assigned."""
        for tp in assigned:
            last_offset = await self.get_last_offset(tp)
            if last_offset < 0:
                await self.consumer.seek_to_beginning(tp)
            else:
                self.consumer.seek(tp, last_offset + 1)

    async def add_offset(self, partition, last_offset, topic):
        """Commit offset to Kafka."""
        self.state[TopicPartition(topic, partition)] = last_offset
        await self.consumer.commit(
            {TopicPartition(topic, partition): OffsetAndMetadata(last_offset, "")}
        )

    async def get_last_offset(self, tp: TopicPartition) -> int:
        """Return last saved offset for a TopicPartition."""
        offset = await self.consumer.committed(tp)
        if offset:
            return offset
        else:
            return -1


class KafkaHandler:
    """Kafka outbound delivery."""

    # for unit testing
    RUNNING = True
    RUNNING_RETRY = True

    def __init__(self, host: str, prefix: str):
        """Initialize KafkaHandler."""
        (self._host, self.username, self.password) = self.parse_connection_url(host)
        self.consumer_retry = None
        self.prefix = prefix
        self.retry_interval = 5
        self.retry_backoff = 0.25
        self.outbound_topic = f"{self.prefix}.outbound_transport"
        self.retry_topic = f"{self.prefix}.outbound_retry"
        self.retry_timedelay_s = 3
        self.consumer = None
        self.producer = None
        self.consumer_retry = None

    def parse_connection_url(self, connection):
        """Retreive bootstrap_server, username and password from provided connection."""
        kafka_username = None
        kafka_password = None
        split_kafka_url_by_hash = connection.rsplit("#", 1)
        if len(split_kafka_url_by_hash) > 1:
            kafka_username = split_kafka_url_by_hash[1].split(":")[0]
            kafka_password = split_kafka_url_by_hash[1].split(":")[1]
        kafka_url = split_kafka_url_by_hash[0]
        return (kafka_url, kafka_username, kafka_password)

    async def run(self):
        """Run the service."""
        self.consumer = AIOKafkaConsumer(
            bootstrap_servers=self._host,
            group_id="my_group",
            enable_auto_commit=False,
            auto_offset_reset="none",
            isolation_level="read_committed",
            sasl_plain_username=self.username,
            sasl_plain_password=self.password,
        )
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self._host,
            enable_idempotence=True,
            transactional_id=str(uuid4()),
            sasl_plain_username=self.username,
            sasl_plain_password=self.password,
        )
        self.consumer_retry = AIOKafkaConsumer(
            bootstrap_servers=self._host,
            group_id="my_group",
            enable_auto_commit=False,
            auto_offset_reset="none",
            isolation_level="read_committed",
            sasl_plain_username=self.username,
            sasl_plain_password=self.password,
        )
        await self.consumer.start()
        await self.producer.start()
        await asyncio.gather(self.process_delivery(), self.process_retries())

    async def process_delivery(self):
        """Process delivery of outbound messages."""
        http_client = aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())
        listener = RebalanceListener(self.consumer)
        self.consumer.subscribe(topics=[self.outbound_topic], listener=listener)
        try:
            while self.RUNNING:
                try:
                    msg_set = await self.consumer.getmany(timeout_ms=1000)
                except OffsetOutOfRangeError as err:
                    tps = err.args[0].keys()
                    await self.consumer.seek_to_beginning(*tps)
                    continue

                for tp, msgs in msg_set.items():
                    for msg in msgs:
                        msg_data = msgpack.unpackb(msg.value)
                        if not isinstance(msg_data, dict):
                            logging.error("Received non-dict message")
                        elif b"endpoint" not in msg_data:
                            logging.error("No endpoint provided")
                        elif b"payload" not in msg_data:
                            logging.error("No payload provided")
                        else:
                            headers = {}
                            if b"headers" in msg_data:
                                for hname, hval in msg_data[b"headers"].items():
                                    if isinstance(hval, bytes):
                                        hval = hval.decode("utf-8")
                                    headers[hname.decode("utf-8")] = hval
                            endpoint = msg_data[b"endpoint"].decode("utf-8")
                            payload = msg_data[b"payload"].decode("utf-8")
                            parsed = urllib.parse.urlparse(endpoint)
                            if parsed.scheme == "http" or parsed.scheme == "https":
                                logging.info(f"Dispatch message to {endpoint}")
                                failed = False
                                try:
                                    response = await http_client.post(
                                        endpoint,
                                        data=payload,
                                        headers=headers,
                                        timeout=10,
                                    )
                                except aiohttp.ClientError:
                                    failed = True
                                except asyncio.TimeoutError:
                                    failed = True
                                else:
                                    if response.status < 200 or response.status >= 300:
                                        logging.error(
                                            "Invalid response code:", response.status
                                        )
                                        failed = True
                                if failed:
                                    logging.exception(f"Delivery failed for {endpoint}")
                                    retries = msg_data.get(b"retries") or 0
                                    if retries < 5:
                                        await self.add_retry(
                                            {
                                                "endpoint": endpoint,
                                                "headers": headers,
                                                "payload": payload,
                                                "retries": retries + 1,
                                            }
                                        )
                                    else:
                                        logging.error(
                                            f"Exceeded max retries for {str(endpoint)}"
                                        )
                            else:
                                logging.error(f"Unsupported scheme: {parsed.scheme}")
                        await listener.add_offset(msg.partition, msg.offset, msg.topic)
        finally:
            await self.consumer.stop()
            await http_client.close()

    async def add_retry(self, message: dict):
        """Add undelivered message for future retries."""
        wait_interval = pow(
            self.retry_interval, 1 + (self.retry_backoff * (message["retries"] - 1))
        )
        retry_time = int(time() + wait_interval)
        message["retry_time"] = retry_time
        async with self.producer.transaction():
            await self.producer.send(
                self.retry_topic,
                value=msgpack.packb(message),
            )

    async def process_retries(self):
        """Process retries."""
        await self.consumer_retry.start()
        listener = RebalanceListener(self.consumer_retry)
        self.consumer_retry.subscribe(topics=[self.retry_topic], listener=listener)
        try:
            while self.RUNNING_RETRY:
                await asyncio.sleep(self.retry_timedelay_s)
                try:
                    msg_set = await self.consumer_retry.getmany(timeout_ms=1000)
                except OffsetOutOfRangeError as err:
                    tps = err.args[0].keys()
                    await self.consumer_retry.seek_to_beginning(*tps)
                    continue
                for tp, msgs in msg_set.items():
                    for msg in msgs:
                        msg_data = msgpack.unpackb(msg.value)
                        retry_time = msg_data[b"retry_time"]
                        async with self.producer.transaction():
                            if int(time()) > retry_time:
                                del msg_data[b"retry_time"]
                                await self.producer.send(
                                    self.outbound_topic,
                                    value=msgpack.packb(msg_data),
                                )
                            else:
                                await self.producer.send(
                                    self.retry_topic,
                                    value=msgpack.packb(msg_data),
                                )
                        await listener.add_offset(msg.partition, msg.offset, msg.topic)
        finally:
            await self.consumer_retry.stop()
            await self.producer.stop()


async def main(args):
    """Start services."""
    args = argument_parser(args)
    if args.outbound_queue:
        host = args.outbound_queue
    else:
        raise SystemExit("No Kafka bootsrap server or host provided.")
    if args.outbound_queue_prefix:
        prefix = args.outbound_queue_prefix
    else:
        prefix = "acapy"
    logging.info(
        f"Starting Kafka outbound delivery service agent with args: {host}, {prefix}"
    )
    handler = KafkaHandler(host, prefix)
    await handler.run()


def argument_parser(args):
    """Argument parser."""
    parser = ArgumentParser(description="Kafka Outbound Delivery Service.")
    parser.add_argument(
        "-oq",
        "--outbound-queue",
        dest="outbound_queue",
        type=str,
        env_var="ACAPY_OUTBOUND_TRANSPORT_QUEUE",
    )
    parser.add_argument(
        "-oqp",
        "--outbound-queue-prefix",
        dest="outbound_queue_prefix",
        type=str,
        default="acapy",
        env_var="ACAPY_OUTBOUND_TRANSPORT_QUEUE_PREFIX",
    )
    return parser.parse_args(args)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main(sys.argv[1:]))
