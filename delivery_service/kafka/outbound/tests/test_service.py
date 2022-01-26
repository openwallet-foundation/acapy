import asyncio
import msgpack
import pytest
import random
import string

from asynctest import TestCase as AsyncTestCase, mock as async_mock, PropertyMock
from aiokafka.errors import OffsetOutOfRangeError
from aiokafka.structs import TopicPartition
from collections import Counter

from .. import service as test_module
from ..service import KafkaHandler, LocalState, RebalanceListener


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
        assert self.local_state._counts == {}
        assert self.local_state._offsets == {}
        test_partition = {
            TopicPartition(topic="topic1", partition=1),
            TopicPartition(topic="topic2", partition=0),
        }
        self.local_state.load_local_state(test_partition)
        assert self.local_state._counts != {}
        assert self.local_state._offsets != {}

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
    def setUp(self):
        self.host = "test"
        self.prefix = "acapy"

    async def test_init(self):
        with async_mock.patch(
            "aiokafka.AIOKafkaProducer.start",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaProducer.stop",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaProducer.transaction",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaProducer.send",
            async_mock.CoroutineMock(),
        ) as mock_send, async_mock.patch(
            "aiokafka.AIOKafkaProducer",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.start",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.stop",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.subscribe",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.getmany",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.seek_to_beginning",
            async_mock.CoroutineMock(),
        ) as mock_seek_to_beginning, async_mock.patch(
            "aiokafka.AIOKafkaConsumer",
            async_mock.MagicMock(),
        ):
            queue = KafkaHandler()
            queue.prefix == "acapy"
            queue.connection = "connection"
            assert str(queue)
            await queue.start()
            await queue.stop()

    async def test_save_state_every_second(self):
        pass

    async def test_process_delivery(self):
        pass

    async def test_add_retry(self):
        pass

    async def test_process_retries(self):
        pass
