"""Redis inbound transport."""
import asyncio
import os
import msgpack
import logging
import json
import pathlib

from aiokafka import AIOKafkaConsumer, ConsumerRebalanceListener
from aiokafka.errors import OffsetOutOfRangeError
from collections import Counter
from threading import Thread

from ....core.profile import Profile
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
        try:
            plugin_config = root_profile.settings["plugin_config"] or {}
            config = plugin_config[self.config_key]
            self.connection = config["connection"]
        except KeyError as error:
            raise InboundQueueConfigurationError(
                "Configuration missing for Kafka queue"
            ) from error

        self.prefix = config.get("prefix", "acapy")
        self.consumer = AIOKafkaConsumer(
            bootstrap_servers=self.connection,
            group_id="my_group",
            enable_auto_commit=False,
            auto_offset_reset="none",
        )

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
        # aioredis will lazily connect but we can eagerly trigger connection with:
        # await self.redis.ping()
        # Calling this on enter to `async with` just before another queue
        # operation is made does not make sense and we should just let aioredis
        # do lazy connection.

    async def stop(self):
        """Stop the transport."""
        # aioredis cleans up automatically but we can clean up manually with:
        # await self.pool.disconnect()
        # However, calling this on exit of `async with` does not make sense and
        # we should just let aioredis handle the connection lifecycle.

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
        await self.consumer.start()
        topic = f"{self.prefix}.inbound_transport"
        local_state = LocalState()
        listener = RebalanceListener(self.consumer, local_state)
        self.consumer.subscribe(topics=[topic], listener=listener)
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
                        elif "transport_type" not in msg and msg[
                            "transport_type"
                        ] not in ["http", "ws"]:
                            self._logger.error(
                                "Received message with invalid transport type specified"
                            )
                            continue
                        async with session:
                            if msg["transport_type"] == "ws":
                                await session.receive(msg["data"])
                            elif msg["transport_type"] == "http":
                                await session.receive(msg["body"])
                        counts[msg.key] += 1
                    local_state.add_counts(tp, counts, msg.offset)
        finally:
            await self.consumer.stop()
            save_task.cancel()
            await save_task
