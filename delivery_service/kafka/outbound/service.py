"""Kafka Outbound Delivery Service."""
import aiohttp
import argparse
import asyncio
import json
import logging
import msgpack
import os
import pathlib
import sys
import urllib
import yaml

from aiokafka import AIOKafkaConsumer, ConsumerRebalanceListener, AIOKafkaProducer
from aiokafka.errors import OffsetOutOfRangeError
from collections import Counter
from time import time

logging.basicConfig(
    format="%(asctime)s | %(levelname)s: %(message)s",
    level=logging.INFO,
    filename="kafka_outbound.log",
    filemode="w",
)


class RebalanceListener(ConsumerRebalanceListener):
    """Listener to control actions before and after rebalance."""

    def __init__(self, consumer, local_state):
        """Initialize RebalanceListener."""
        self.consumer = consumer
        self.local_state = local_state

    async def on_partitions_revoked(self, revoked):
        """Triggered on partitions revocation."""
        self.local_state.dump_local_state()

    async def on_partitions_assigned(self, assigned):
        """Triggered on partitions assigned."""
        self.local_state.load_local_state(assigned)
        for tp in assigned:
            last_offset = self.local_state.get_last_offset(tp)
            if last_offset < 0:
                await self.consumer.seek_to_beginning(tp)
            else:
                self.consumer.seek(tp, last_offset + 1)


class LocalState:
    """Handle local json storage file for storing offsets."""

    OFFSET_LOCAL_FILE = os.path.join(
        os.path.dirname(__file__), "partition-state-inbound_queue.json"
    )

    def __init__(self):
        """Initialize LocalState."""
        self._counts = {}
        self._offsets = {}

    def dump_local_state(self):
        """Dump local state."""
        for tp in self._counts:
            fpath = pathlib.Path(self.OFFSET_LOCAL_FILE)
            with fpath.open("w+") as f:
                json.dump(
                    {
                        "last_offset": self._offsets[tp],
                        "counts": dict(self._counts[tp]),
                    },
                    f,
                )

    def load_local_state(self, partitions):
        """Load local state."""
        self._counts.clear()
        self._offsets.clear()
        for tp in partitions:
            fpath = pathlib.Path(self.OFFSET_LOCAL_FILE)
            state = {"last_offset": -1, "counts": {}}  # Non existing, will reset
            if fpath.exists():
                with fpath.open("r+") as f:
                    try:
                        state = json.load(f)
                    except json.JSONDecodeError:
                        pass
            self._counts[tp] = Counter(state["counts"])
            self._offsets[tp] = state["last_offset"]

    def add_counts(self, tp, counts, last_offset):
        """Update offsets and count."""
        self._counts[tp] += counts
        self._offsets[tp] = last_offset

    def get_last_offset(self, tp):
        """Return last offset."""
        return self._offsets[tp]

    def discard_state(self, tps):
        """Discard a state."""
        for tp in tps:
            self._offsets[tp] = -1
            self._counts[tp] = Counter()


class KafkaHandler:
    """Kafka outbound delivery."""

    # for unit testing
    RUNNING = True
    RUNNING_RETRY = True

    def __init__(self, host: str, prefix: str):
        """Initialize KafkaHandler."""
        self._host = host
        self.consumer_retry = None
        self.prefix = prefix
        self.retry_interval = 5
        self.retry_backoff = 0.25
        self.outbound_topic = f"{self.prefix}.outbound_transport"
        self.retry_topic = f"{self.prefix}.outbound_retry"
        self.retry_timedelay_s = 3
        self.consumer = AIOKafkaConsumer(
            bootstrap_servers=self._host,
            group_id="my_group",
            enable_auto_commit=False,
            auto_offset_reset="none",
            isolation_level="read_committed",
        )
        self.consumer_retry = AIOKafkaConsumer(
            bootstrap_servers=self._host,
            group_id="my_group",
            enable_auto_commit=False,
            auto_offset_reset="none",
            isolation_level="read_committed",
        )
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self._host, enable_idempotence=True
        )

    async def run(self):
        """Run the service."""
        await self.consumer.start()
        await self.producer.start()
        await asyncio.gather(self.process_delivery(), self.process_retries())

    async def save_state_every_second(self, local_state):
        """Update local state."""
        while self.RUNNING:
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            local_state.dump_local_state()

    async def process_delivery(self):
        """Process delivery of outbound messages."""
        http_client = aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())
        local_state = LocalState()
        listener = RebalanceListener(self.consumer, local_state)
        self.consumer.subscribe(topics=[self.outbound_topic], listener=listener)
        loop = asyncio.get_event_loop()
        save_task = loop.create_task(self.save_state_every_second(local_state))
        try:
            while self.RUNNING:
                try:
                    msg_set = await self.consumer.getmany(timeout_ms=1000)
                except OffsetOutOfRangeError as err:
                    tps = err.args[0].keys()
                    local_state.discard_state(tps)
                    await self.consumer.seek_to_beginning(*tps)
                    continue

                for tp, msgs in msg_set.items():
                    counts = Counter()
                    for msg in msgs:
                        msg_data = msgpack.unpackb(msg.value)
                        if not isinstance(msg_data, dict):
                            logging.error("Received non-dict message")
                        elif "endpoint" not in msg_data:
                            logging.error("No endpoint provided")
                        elif "payload" not in msg_data:
                            logging.error("No payload provided")
                        else:
                            headers = {}
                            if "headers" in msg_data:
                                for hname, hval in msg_data["headers"].items():
                                    if isinstance(hval, bytes):
                                        hval = hval.decode("utf-8")
                                    headers[hname] = hval
                            endpoint = msg_data["endpoint"]
                            payload = msg_data["payload"]
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
                                except aiohttp.ClientError as err:
                                    logging.error("Delivery error:", err)
                                    failed = True
                                else:
                                    if response.status < 200 or response.status >= 300:
                                        logging.error(
                                            "Invalid response code:", response.status
                                        )
                                        failed = True
                                if failed:
                                    retries = msg_data.get("retries") or 0
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
                                            "Exceeded max retries for", endpoint
                                        )
                            else:
                                logging.error(f"Unsupported scheme: {parsed.scheme}")
                        counts[msg.key] += 1
                    local_state.add_counts(tp, counts, msg.offset)
        finally:
            await self.consumer.stop()
            await http_client.close()
            save_task.cancel()
            await asyncio.wait([save_task], return_when=asyncio.FIRST_COMPLETED)

    async def add_retry(self, message: dict):
        """Add undelivered message for future retries."""
        wait_interval = pow(
            self.retry_interval, 1 + (self.retry_backoff * (message["retries"] - 1))
        )
        retry_time = int(time() + wait_interval)
        message["retry_time"] = retry_time
        await self.producer.send(
            self.retry_topic,
            value=msgpack.packb(message),
        )

    async def process_retries(self):
        """Process retries."""
        await self.consumer_retry.start()
        local_state = LocalState()
        listener = RebalanceListener(self.consumer_retry, local_state)
        self.consumer_retry.subscribe(topics=[self.retry_topic], listener=listener)
        loop = asyncio.get_event_loop()
        save_task = loop.create_task(self.save_state_every_second(local_state))
        try:
            while self.RUNNING_RETRY:
                await asyncio.sleep(self.retry_timedelay_s)
                try:
                    msg_set = await self.consumer_retry.getmany(timeout_ms=1000)
                except OffsetOutOfRangeError as err:
                    tps = err.args[0].keys()
                    local_state.discard_state(tps)
                    await self.consumer_retry.seek_to_beginning(*tps)
                    continue
                for tp, msgs in msg_set.items():
                    counts = Counter()
                    for msg in msgs:
                        msg_data = msgpack.unpackb(msg.value)
                        retry_time = msg_data["retry_time"]
                        if int(time()) > retry_time:
                            del msg_data["retry_time"]
                            await self.producer.send(
                                self.outbound_topic,
                                value=msgpack.packb(msg_data),
                            )
                        counts[msg.key] += 1
                    local_state.add_counts(tp, counts, msg.offset)
        finally:
            await self.consumer_retry.stop()
            await self.producer.stop()
            save_task.cancel()
            await asyncio.wait([save_task], return_when=asyncio.FIRST_COMPLETED)


async def main(args):
    """Start services."""
    args = argument_parser(args)
    config = None
    if args.plugin_config:
        with open(args.plugin_config, "r") as stream:
            loaded_plugin_config = yaml.safe_load(stream)
        config = loaded_plugin_config.get("kafka_outbound_queue")
    if args.outbound_queue:
        host = args.outbound_queue
    elif config:
        host = config["connection"]
    else:
        raise SystemExit("No Kafka bootsrap server or host provided.")
    if config:
        prefix = config.get("prefix", "acapy")
    elif args.outbound_queue_prefix:
        prefix = args.outbound_queue_prefix
    handler = KafkaHandler(host, prefix)
    await handler.run()


def argument_parser(args):
    """Argument parser."""
    parser = argparse.ArgumentParser(description="Kafka Outbound Delivery Service.")
    parser.add_argument(
        "-oq",
        "--outbound-queue",
        dest="outbound_queue",
        type=str,
    )
    parser.add_argument(
        "-oqp",
        "--outbound-queue-prefix",
        dest="outbound_queue_prefix",
        type=str,
        default="acapy",
    )
    parser.add_argument(
        "--plugin-config",
        dest="plugin_config",
        type=str,
        required=False,
        help="Load YAML file path that defines external plugin configuration.",
    )
    return parser.parse_args(args)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main(sys.argv[1:]))
