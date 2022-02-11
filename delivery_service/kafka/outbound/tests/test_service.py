import msgpack
import os
import pytest
import random
import string
import json

import aiohttp
import asyncio
from asynctest import TestCase as AsyncTestCase, mock as async_mock, PropertyMock
from aiokafka.errors import OffsetOutOfRangeError
from aiokafka.structs import TopicPartition
from collections import Counter
from pathlib import Path
from time import time

from .. import service as test_module
from ..service import KafkaHandler, LocalState, RebalanceListener, main, argument_parser

test_msg_sets_a = {
    "acapy.outbound_transport": [
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    b"headers": {b"content-type": b"test"},
                    b"endpoint": b"http://localhost:9000",
                    b"payload": (string.digits + string.ascii_letters).encode("utf-8"),
                }
            ),
            key="test_random_2",
            offsets=1003,
        ),
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    b"headers": {b"content-type": b"test1"},
                    b"endpoint": b"http://localhost:9000",
                    b"payload": (string.digits + string.ascii_letters).encode("utf-8"),
                }
            ),
            key="test_random_3",
            offsets=1002,
        ),
    ]
}
test_msg_sets_b = {
    "acapy.outbound_transport": [
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    b"headers": {b"content-type": b"test1"},
                    b"endpoint": b"http://localhost:9000",
                    b"payload": (string.digits + string.ascii_letters).encode("utf-8"),
                }
            ),
            key="test_random_1",
            offsets=1001,
        )
    ]
}
test_msg_sets_c = {
    "acapy.outbound_transport": [
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    b"headers": {b"content-type": b"test1"},
                    b"endpoint": b"http://localhost:9000",
                    b"payload": (string.digits + string.ascii_letters).encode("utf-8"),
                    b"retries": 6,
                }
            ),
            key="test_random_1",
            offsets=1001,
        )
    ]
}
test_msg_sets_d = {
    "acapy.outbound_transport": [
        async_mock.MagicMock(
            value=msgpack.packb(["invalid", "list", "require", "dict"]),
            key="test_random_1",
            offsets=1001,
        ),
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    b"headers": {b"content-type": b"test1"},
                    "payload": (string.digits + string.ascii_letters).encode("utf-8"),
                }
            ),
            key="test_random_1",
            offsets=1001,
        ),
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    "headers": {b"content-type": b"test1"},
                    b"endpoint": b"http://localhost:9000",
                    b"payload": (string.digits + string.ascii_letters).encode("utf-8"),
                    b"retries": 6,
                }
            ),
            key="test_random_1",
            offsets=1001,
        ),
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    b"headers": {b"content-type": b"test1"},
                    "endpoint": b"ws://localhost:9000",
                    b"payload": (string.digits + string.ascii_letters).encode("utf-8"),
                }
            ),
            key="test_random_1",
            offsets=1001,
        ),
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    b"headers": {b"content-type": b"test1"},
                    b"endpoint": b"ws://localhost:9000",
                    b"payload": (string.digits + string.ascii_letters).encode("utf-8"),
                }
            ),
            key="test_random_1",
            offsets=1001,
        ),
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    b"headers": {b"content-type": "test1"},
                    b"endpoint": b"ws://localhost:9000",
                }
            ),
            key="test_random_1",
            offsets=1001,
        ),
    ]
}
test_msg_sets_e = {
    "acapy.outbound_retry": [
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    b"headers": {b"content-type": b"test1"},
                    b"endpoint": b"http://localhost:9000",
                    b"payload": (string.digits + string.ascii_letters).encode("utf-8"),
                    b"retry_time": int(time()),
                }
            ),
            key="test_random_1",
            offsets=1001,
        )
    ]
}
offset_local_path = os.path.join(
    os.path.dirname(__file__),
    "test-partition-state-inbound_queue.json",
)


class TestRebalanceListener(AsyncTestCase):
    def setUp(self):
        self.test_partition = {
            TopicPartition(topic="topic1", partition=1),
            TopicPartition(topic="topic2", partition=0),
        }
        self.mock_consumer = async_mock.MagicMock(
            seek_to_beginning=async_mock.CoroutineMock(),
            seek=async_mock.CoroutineMock(),
        )
        self.mock_local_state = async_mock.MagicMock(
            dump_local_state=async_mock.MagicMock(),
            load_local_state=async_mock.MagicMock(),
            get_last_offset=async_mock.MagicMock(return_value=-1),
        )
        self.listener = RebalanceListener(self.mock_consumer, self.mock_local_state)

    async def test_on_partitions_revoked(self):
        await self.listener.on_partitions_revoked(self.test_partition)

    async def test_on_partitions_assigned_a(self):
        await self.listener.on_partitions_assigned(self.test_partition)

    async def test_on_partitions_assigned_b(self):
        self.mock_local_state = async_mock.MagicMock(
            dump_local_state=async_mock.MagicMock(),
            load_local_state=async_mock.MagicMock(),
            get_last_offset=async_mock.MagicMock(return_value=1),
        )
        self.listener = RebalanceListener(self.mock_consumer, self.mock_local_state)
        await self.listener.on_partitions_assigned(self.test_partition)


class TestLocalState(AsyncTestCase):
    def setUp(self):
        self.local_state = LocalState()
        self.local_state.OFFSET_LOCAL_FILE = offset_local_path
        assert self.local_state._counts == {}
        assert self.local_state._offsets == {}
        self.test_partition = {
            TopicPartition(topic="topic1", partition=1),
            TopicPartition(topic="topic2", partition=0),
        }
        with async_mock.patch.object(
            test_module.pathlib, "Path", async_mock.MagicMock()
        ) as pathlib_obj, async_mock.patch.object(
            test_module.json,
            "load",
            async_mock.MagicMock(
                return_value={"last_offset": 10, "counts": {"key": 5}}
            ),
        ):
            pathlib_obj.exists = async_mock.CoroutineMock(return_value=True)
            pathlib_obj.open = async_mock.MagicMock()
            self.local_state.load_local_state(self.test_partition)
        assert self.local_state._counts != {}
        assert self.local_state._offsets != {}

    def test_load_local_state_x(self):
        with async_mock.patch.object(
            test_module.pathlib, "Path", async_mock.MagicMock()
        ) as pathlib_obj, async_mock.patch.object(
            test_module.json,
            "load",
            async_mock.MagicMock(
                side_effect=test_module.json.JSONDecodeError("test", "test", 1)
            ),
        ):
            pathlib_obj.exists = async_mock.CoroutineMock(return_value=True)
            pathlib_obj.open = async_mock.MagicMock()
            self.local_state.load_local_state(self.test_partition)

    def test_dump_local_state(self):
        self.local_state.dump_local_state()

    def test_utility_functions(self):
        counts = Counter()
        counts[123] += 1
        counts[456] += 1
        self.local_state.add_counts(
            TopicPartition(topic="topic1", partition=1), counts, 100
        )
        assert (
            self.local_state.get_last_offset(
                TopicPartition(topic="topic1", partition=1)
            )
            == 100
        )
        assert (
            self.local_state._counts[TopicPartition(topic="topic1", partition=1)]
            != Counter()
        )
        assert (
            self.local_state._offsets[TopicPartition(topic="topic1", partition=1)] != -1
        )
        self.local_state.discard_state([TopicPartition(topic="topic1", partition=1)])
        assert (
            self.local_state._counts[TopicPartition(topic="topic1", partition=1)]
            == Counter()
        )
        assert (
            self.local_state._offsets[TopicPartition(topic="topic1", partition=1)] == -1
        )


class TestKafkaHandler(AsyncTestCase):
    async def test_main(self):
        KafkaHandler.RUNNING = PropertyMock(side_effect=[True, True, False])
        with async_mock.patch(
            "aiokafka.AIOKafkaProducer.start",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaProducer",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.start",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer",
            async_mock.MagicMock(),
        ), async_mock.patch.object(
            KafkaHandler, "process_delivery", autospec=True
        ), async_mock.patch.object(
            KafkaHandler, "process_retries", autospec=True
        ), async_mock.patch.object(
            Path, "open", async_mock.MagicMock()
        ):
            await main(
                [
                    "-oq",
                    "test",
                ]
            )

    async def test_main_x(self):
        with self.assertRaises(SystemExit):
            await main([])

    async def test_save_state_every_second(self):
        sentinel = PropertyMock(side_effect=[True, True, True, False])
        KafkaHandler.RUNNING = sentinel
        service = KafkaHandler("test", "acapy")
        with async_mock.patch.object(
            test_module, "LocalState", autospec=True
        ) as mock_local_state, async_mock.patch.object(
            test_module.asyncio,
            "sleep",
            async_mock.CoroutineMock(
                side_effect=[None, None, test_module.asyncio.CancelledError]
            ),
        ):
            await service.save_state_every_second(mock_local_state)
        assert mock_local_state.dump_local_state.call_count == 2

    async def test_process_delivery(self):
        sentinel = PropertyMock(side_effect=[True, True, False])
        KafkaHandler.RUNNING = sentinel
        service = KafkaHandler("test", "acapy")
        with async_mock.patch.object(
            aiohttp.ClientSession,
            "post",
            async_mock.CoroutineMock(return_value=async_mock.MagicMock(status=200)),
        ), async_mock.patch.object(
            test_module, "LocalState", autospec=True
        ) as mock_local_state, async_mock.patch.object(
            KafkaHandler, "save_state_every_second", autospec=True
        ), async_mock.patch.object(
            service, "process_retries", async_mock.CoroutineMock()
        ):
            mock_producer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                transaction=async_mock.MagicMock(),
                send=async_mock.CoroutineMock(),
            )

            mock_consumer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                subscribe=async_mock.CoroutineMock(),
                getmany=async_mock.CoroutineMock(
                    side_effect=[
                        test_msg_sets_a,
                        test_msg_sets_b,
                    ]
                ),
                seek_to_beginning=async_mock.CoroutineMock(),
            )
            service.consumer = mock_consumer
            service.producer = mock_producer
            await service.process_delivery()

    async def test_process_delivery_x(self):
        sentinel = PropertyMock(side_effect=[True, True, True, True, False])
        KafkaHandler.RUNNING = sentinel
        service = KafkaHandler("test", "acapy")
        with async_mock.patch.object(
            aiohttp.ClientSession,
            "post",
            async_mock.CoroutineMock(
                side_effect=[
                    async_mock.MagicMock(status=400),
                    aiohttp.ClientError,
                    asyncio.TimeoutError,
                ]
            ),
        ), async_mock.patch.object(
            test_module, "LocalState", autospec=True
        ) as mock_local_state, async_mock.patch.object(
            KafkaHandler, "save_state_every_second", autospec=True
        ), async_mock.patch.object(
            service, "process_retries", async_mock.CoroutineMock()
        ):
            mock_producer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                transaction=async_mock.MagicMock(),
                send=async_mock.CoroutineMock(),
            )

            mock_consumer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                subscribe=async_mock.CoroutineMock(),
                getmany=async_mock.CoroutineMock(
                    side_effect=[
                        OffsetOutOfRangeError({}),
                        test_msg_sets_d,
                        test_msg_sets_b,
                        test_msg_sets_b,
                    ]
                ),
                seek_to_beginning=async_mock.CoroutineMock(),
            )
            service.consumer = mock_consumer
            service.producer = mock_producer
            await service.process_delivery()

    async def test_process_retries(self):
        sentinel = PropertyMock(side_effect=[True, True, False])
        KafkaHandler.RUNNING_RETRY = sentinel
        service = KafkaHandler("test", "acapy")
        service.retry_timedelay_s = 0.1
        with async_mock.patch.object(
            test_module, "LocalState", autospec=True
        ) as mock_local_state, async_mock.patch.object(
            KafkaHandler, "save_state_every_second", autospec=True
        ):
            mock_producer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                transaction=async_mock.MagicMock(),
                send=async_mock.CoroutineMock(),
            )

            mock_consumer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                subscribe=async_mock.CoroutineMock(),
                getmany=async_mock.CoroutineMock(
                    side_effect=[
                        OffsetOutOfRangeError({}),
                        test_msg_sets_e,
                    ]
                ),
                seek_to_beginning=async_mock.CoroutineMock(),
            )
            service.consumer_retry = mock_consumer
            service.producer = mock_producer
            await service.process_retries()
