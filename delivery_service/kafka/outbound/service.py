import asyncio
import aiohttp
import msgpack
import sys
import json
import os
import pathlib
import urllib

from aiokafka import AIOKafkaConsumer, ConsumerRebalanceListener, AIOKafkaProducer
from aiokafka.errors import OffsetOutOfRangeError
from collections import Counter
from uuid import uuid4


def log_error(*args):
    print(*args, file=sys.stderr)


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


class KafkaHandler:
    def __init__(self, host: str, prefix: str, retry_timedelay_s: int = 15):
        self._host = host
        self.consumer = None
        self.prefix = prefix
        self.retry_timedelay_s = retry_timedelay_s

    async def run(self):
        self.consumer = AIOKafkaConsumer(
            bootstrap_servers=self._host,
            group_id="my_group",
            enable_auto_commit=False,
            auto_offset_reset="none",
        )
        self.consumer_retry = AIOKafkaConsumer(
            bootstrap_servers=self._host,
            group_id="my_group",
            enable_auto_commit=False,
            auto_offset_reset="none",
        )
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.connection, transactional_id=str(uuid4())
        )
        await self.consumer.start()
        await self.consumer_retry.start()
        await self.producer.start()
        await asyncio.gather(self.process_delivery(), self.process_retries())

    async def save_state_every_second(self, local_state):
        """Update local state."""
        while True:
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            local_state.dump_local_state()

    async def process_delivery(self):
        http_client = aiohttp.ClientSession(cookie_jar=aiohttp.DummyCookieJar())
        print("Listening for messages..")
        topic = f"{self.prefix}.outbound_transport"
        local_state = LocalState()
        listener = RebalanceListener(self.consumer, local_state)
        self.consumer.subscribe(topics=[topic], listener=listener)
        save_task = asyncio.create_task(self.save_state_every_second(local_state))
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
                            log_error("Received non-dict message")
                        elif b"endpoint" not in msg:
                            log_error("No endpoint provided")
                        elif b"payload" not in msg:
                            log_error("No payload provided")
                        else:
                            headers = {}
                            if b"headers" in msg:
                                for hname, hval in msg[b"headers"].items():
                                    if isinstance(hval, bytes):
                                        hval = hval.decode("utf-8")
                                    headers[hname.decode("utf-8")] = hval
                            endpoint = msg[b"endpoint"].decode("utf-8")
                            payload = msg[b"payload"]
                            parsed = urllib.parse.urlparse(endpoint)
                            if parsed.scheme == "http" or parsed.scheme == "https":
                                print(f"Dispatch message to {endpoint}")
                                failed = False
                                try:
                                    response = await http_client.post(
                                        endpoint,
                                        data=payload,
                                        headers=headers,
                                        timeout=10,
                                    )
                                except aiohttp.ClientError as err:
                                    log_error("Delivery error:", err)
                                    failed = True
                                else:
                                    if response.status < 200 or response.status >= 300:
                                        log_error(
                                            "Invalid response code:", response.status
                                        )
                                        failed = True
                                if failed:
                                    retries = msg.get(b"retries") or 0
                                    if retries < 5:
                                        await self.add_retry(
                                            {
                                                "endpoint": endpoint,
                                                "headers": headers,
                                                "payload": payload,
                                            }
                                        )
                                    else:
                                        log_error("Exceeded max retries for", endpoint)
                            else:
                                log_error(f"Unsupported scheme: {parsed.scheme}")
                        counts[msg.key] += 1
                    local_state.add_counts(tp, counts, msg.offset)
        finally:
            await self.consumer.stop()
            save_task.cancel()
            await save_task

    async def add_retry(self, message: dict):
        async with self.producer.transaction():
            await self.producer.send(
                f"{self.prefix}.outbound_retry",
                value=msgpack.dumps(message),
                timestamp_ms=1000,
            )

    async def process_retries(self):
        outbound_topic = f"{self.prefix}.outbound_transport"
        retry_topic = f"{self.prefix}.outbound_retry"
        local_state = LocalState()
        listener = RebalanceListener(self.consumer_retry, local_state)
        self.consumer_retry.subscribe(topics=[retry_topic], listener=listener)
        save_task = asyncio.create_task(self.save_state_every_second(local_state))
        try:
            while True:
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
                        async with self.producer.transaction():
                            await self.producer.send(
                                outbound_topic, value=msg, timestamp_ms=1000
                            )
                        counts[msg.key] += 1
                    local_state.add_counts(tp, counts, msg.offset)
        finally:
            await self.consumer_retry.stop()
            await self.producer.stop()
            save_task.cancel()
            await save_task


async def main(host: str, topic: str):
    handler = KafkaHandler(host, topic)
    await handler.run()


if __name__ == "__main__":
    args = sys.argv
    if len(args) <= 1:
        raise SystemExit("Pass redis host URL as the first parameter")
    if len(args) > 2:
        topic = args[2]
    else:
        topic = "acapy"

    asyncio.get_event_loop().run_until_complete(main(args[1], topic))
