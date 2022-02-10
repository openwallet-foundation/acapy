"""Redis inbound transport."""
import asyncio
import os
import msgpack
import json
import logging
import pathlib

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, ConsumerRebalanceListener
from aiokafka.errors import OffsetOutOfRangeError
from collections import Counter
from random import randrange
from threading import Thread

from ....core.profile import Profile

from ...wire_format import DIDCOMM_V0_MIME_TYPE, DIDCOMM_V1_MIME_TYPE

from ..manager import InboundTransportManager

from .base import BaseInboundQueue, InboundQueueConfigurationError


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
            key_deserializer=lambda key: key.decode("utf-8") if key else "",
        )
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.connection,
            enable_idempotence=True,
        )
        await self.producer.start()
        await self.consumer.start()
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.receive_messages(), loop=loop)

    async def stop_queue(self):
        """Stop the transport."""
        await self.producer.stop()
        await self.consumer.stop()

    async def save_state_every_second(self, local_state):
        """Update local state."""
        while self.RUNNING:
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            local_state.dump_local_state()

    async def open(self):
        """Kafka connection context manager enter."""

    async def close(self):
        """Kafka connection context manager exit."""
        if not self.producer._closed:
            await self.producer.start()

    async def receive_messages(
        self,
    ):
        """Recieve message from inbound queue and handle it."""
        transport_manager = self._profile.context.injector.inject(
            InboundTransportManager
        )
        local_state = LocalState()
        listener = RebalanceListener(self.consumer, local_state)
        self.consumer.subscribe(topics=[self.inbound_topic], listener=listener)
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
                                await self.producer.send(
                                    self.direct_response_topic,
                                    value=msgpack.packb(message),
                                    key=(
                                        f"{self.direct_response_topic}_"
                                        f"{str(randrange(5))}".encode("utf-8")
                                    ),
                                )
                        counts[msg.key] += 1
                    local_state.add_counts(tp, counts, msg.offset)
        finally:
            await self.producer.stop()
            await self.consumer.stop()
            save_task.cancel()
            await asyncio.wait([save_task], return_when=asyncio.FIRST_COMPLETED)
