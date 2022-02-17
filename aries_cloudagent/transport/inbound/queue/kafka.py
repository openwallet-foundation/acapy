"""Kafka inbound transport."""
import asyncio
import msgpack
import logging

from aiokafka import (
    AIOKafkaConsumer,
    AIOKafkaProducer,
    ConsumerRebalanceListener,
    OffsetAndMetadata,
    TopicPartition,
)
from aiokafka.errors import OffsetOutOfRangeError
from threading import Thread
from uuid import uuid4

from ....core.profile import Profile

from ...wire_format import DIDCOMM_V0_MIME_TYPE, DIDCOMM_V1_MIME_TYPE

from ..manager import InboundTransportManager

from .base import BaseInboundQueue, InboundQueueConfigurationError


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


class KafkaInboundQueue(BaseInboundQueue, Thread):
    """Kafka outbound transport class."""

    config_key = "kafka_inbound_queue"
    # for unit testing
    RUNNING = True

    def __init__(self, root_profile: Profile) -> None:
        """Set initial state."""
        Thread.__init__(self)
        self._profile = root_profile
        self.logger = logging.getLogger(__name__)
        try:
            plugin_config = root_profile.settings.get("plugin_config", {})
            config = plugin_config.get(self.config_key, {})
            self.connection = (
                self._profile.settings.get("transport.inbound_queue")
                or config["connection"]
            )
        except KeyError as error:
            raise InboundQueueConfigurationError(
                "Configuration missing for Kafka queue"
            ) from error
        (self.connection, self.username, self.password) = self.parse_connection_url(
            self.connection
        )
        self.prefix = self._profile.settings.get(
            "transport.inbound_queue_prefix"
        ) or config.get("prefix", "acapy")
        self.inbound_topic = f"{self.prefix}.inbound_transport"
        self.direct_response_topic = f"{self.prefix}.inbound_direct_responses"
        self.listener_config = self._profile.settings.get(
            "transport.inbound_queue_transports", []
        )
        self.listener_urls = []
        for transport in self.listener_config:
            module, host, port = transport
            self.listener_urls.append(f"{module}://{host}:{port}")
        self.consumer = None
        self.producer = None

    def __str__(self):
        """Return string representation of the outbound queue."""
        return f"KafkaInboundQueue({self.prefix}, " f"{self.connection})"

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

    def sanitize_connection_url(self) -> str:
        """Return sanitized connection with no secrets included."""
        return self.connection

    async def start_queue(self):
        """Start the transport."""
        self.daemon = True
        self.start()
        self.consumer = AIOKafkaConsumer(
            bootstrap_servers=self.connection,
            group_id="my_group",
            enable_auto_commit=False,
            auto_offset_reset="none",
            isolation_level="read_committed",
            sasl_plain_username=self.username,
            sasl_plain_password=self.password,
        )
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.connection,
            transactional_id=str(uuid4()),
            enable_idempotence=True,
            sasl_plain_username=self.username,
            sasl_plain_password=self.password,
        )
        await self.producer.start()
        await self.consumer.start()
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.receive_messages(), loop=loop)

    async def stop_queue(self):
        """Stop the transport."""
        await self.producer.stop()
        await self.consumer.stop()

    async def open(self):
        """Kafka connection context manager enter."""

    async def close(self):
        """Kafka connection context manager exit."""
        if self.producer._closed:
            await self.producer.start()

    async def receive_messages(
        self,
    ):
        """Recieve message from inbound queue and handle it."""
        transport_manager = self._profile.context.injector.inject(
            InboundTransportManager
        )
        listener = RebalanceListener(self.consumer)
        self.consumer.subscribe(topics=[self.inbound_topic], listener=listener)
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
                            self.logger.error("Received non-dict message")
                            continue
                        client_info = {
                            "host": msg_data["host"],
                            "remote": msg_data["remote"],
                        }
                        transport_type = msg_data["transport_type"]
                        session = await transport_manager.create_session(
                            transport_type=transport_type,
                            accept_undelivered=True,
                            can_respond=True,
                            client_info=client_info,
                        )
                        direct_reponse_requested = (
                            True if "txn_id" in msg_data else False
                        )
                        async with session:
                            await session.receive(msg_data["data"].encode("utf-8"))
                            if direct_reponse_requested:
                                txn_id = msg_data["txn_id"]
                                response = await session.wait_response()
                                response_data = {}
                                if transport_type == "http" and response:
                                    if isinstance(response, bytes):
                                        if session.profile.settings.get(
                                            "emit_new_didcomm_mime_type"
                                        ):
                                            response_data[
                                                "content-type"
                                            ] = DIDCOMM_V1_MIME_TYPE
                                        else:
                                            response_data[
                                                "content-type"
                                            ] = DIDCOMM_V0_MIME_TYPE
                                    else:
                                        response_data[
                                            "content-type"
                                        ] = "application/json"
                                response_data["response"] = response
                                message = {}
                                message["txn_id"] = txn_id
                                message["response_data"] = response_data
                                async with self.producer.transaction():
                                    await self.producer.send(
                                        self.direct_response_topic,
                                        value=msgpack.packb(message),
                                    )
                        await listener.add_offset(msg.partition, msg.offset, msg.topic)
        finally:
            await self.producer.stop()
            await self.consumer.stop()
