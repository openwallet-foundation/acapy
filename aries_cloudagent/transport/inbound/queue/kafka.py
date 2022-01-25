"""Redis inbound transport."""
import asyncio
import os
import msgpack
import logging
import json
import pathlib

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, ConsumerRebalanceListener
from aiokafka.errors import OffsetOutOfRangeError
from collections import Counter
from threading import Thread
from uuid import uuid4

from ....core.profile import Profile

from ...wire_format import DIDCOMM_V0_MIME_TYPE, DIDCOMM_V1_MIME_TYPE

from .base import BaseInboundQueue, InboundQueueConfigurationError

OFFSET_LOCAL_FILE = os.path.join(
    os.path.dirname(__file__), "partition-state-inbound_queue.json"
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

    def __init__(self):
        """Initialize LocalState."""
        self._counts = {}
        self._offsets = {}

    def dump_local_state(self):
        """Dump local state."""
        for tp in self._counts:
            fpath = pathlib.Path(OFFSET_LOCAL_FILE)
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
            fpath = pathlib.Path(OFFSET_LOCAL_FILE)
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

    def __init__(self, root_profile: Profile) -> None:
        """Set initial state."""
        self._logger = logging.getLogger(__name__)
        self._profile = root_profile
        try:
            plugin_config = root_profile.settings.get("plugin_config", {})
            config = plugin_config.get(self.config_key, {})
            self.connection = (
                self._profile.settings.get("transport.inbound_queue")
                or config["connection"]
            )
            self.txn_id = config.get("transaction_id", str(uuid4()))
        except KeyError as error:
            raise InboundQueueConfigurationError(
                "Configuration missing for Kafka queue"
            ) from error

        self.prefix = self._profile.settings.get(
            "transport.inbound_queue_prefix"
        ) or config.get("prefix", "acapy")
        self.consumer = None
        self.producer = None

    def __str__(self):
        """Return string representation of the outbound queue."""
        return (
            f"KafkaInboundQueue("
            f"connection={self.connection}, "
            f"prefix={self.prefix}"
            f")"
        )

    async def start(self):
        """Start the transport."""
        self.consumer = AIOKafkaConsumer(
            bootstrap_servers=self.connection,
            group_id="my_group",
            enable_auto_commit=False,
            auto_offset_reset="none",
            isolation_level="read_committed",
        )
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.connection, transactional_id=self.txn_id
        )
        await self.producer.start()
        await self.consumer.start()

    async def stop(self):
        """Stop the transport."""
        await self.producer.stop()
        await self.consumer.stop()

    async def save_state_every_second(self, local_state):
        """Update local state."""
        while True:
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            local_state.dump_local_state()

    async def recieve_messages(
        self,
    ):
        """Recieve message from inbound queue and handle it."""
        inbound_topic = f"{self.prefix}.inbound_transport"
        direct_response_topic = f"{self.prefix}.inbound_direct_responses"
        local_state = LocalState()
        listener = RebalanceListener(self.consumer, local_state)
        self.consumer.subscribe(topics=[inbound_topic], listener=listener)
        save_task = asyncio.create_task(self.save_state_every_second(local_state))
        session = await self.create_session(accept_undelivered=True, can_respond=False)
        try:
            while True:
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
                        msg = msgpack.unpackb(msg)
                        if not isinstance(msg, dict):
                            self._logger.error("Received non-dict message")
                            continue
                        direct_reponse_requested = True if "txn_id" in msg else False
                        async with session:
                            await session.receive(msg["data"].decode("utf-8"))
                            if direct_reponse_requested:
                                txn_id = msg["txn_id"]
                                transport_type = msg["transport_type"]
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
                                response_data["response"] = response.encode("utf-8")
                                message = {}
                                message["txn_id"] = txn_id
                                message["response_data"] = response_data
                                async with self.producer.transaction():
                                    await self.producer.send(
                                        direct_response_topic,
                                        value=msgpack.dumps(message),
                                        timestamp_ms=1000,
                                    )
                        counts[msg.key] += 1
                    local_state.add_counts(tp, counts, msg.offset)
        finally:
            await self.consumer.stop()
            save_task.cancel()
            await save_task
