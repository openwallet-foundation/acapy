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
from ..service import KafkaHTTPHandler, KafkaWSHandler


class TestKafkaHTTPHandler(AsyncTestCase):
    def setUp(self):
        self.host = "test"
        self.prefix = "acapy"
        self.site_host = ""
        self.site_port = ""

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
            queue = KafkaHTTPHandler()
            queue.prefix == "acapy"
            queue.connection = "connection"
            assert str(queue)
            await queue.start()
            await queue.stop()

    async def test_process_direct_responses(self):
        pass

    async def test_get_direct_responses(self):
        pass

    async def test_invite_handler(self):
        pass

    async def test_message_handler(self):
        pass

class TestKafkaWSHandler(AsyncTestCase):
    def setUp(self):
        self.host = "test"
        self.prefix = "acapy"
        self.site_host = ""
        self.site_port = ""

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
            queue = KafkaHTTPHandler()
            queue.prefix == "acapy"
            queue.connection = "connection"
            assert str(queue)
            await queue.start()
            await queue.stop()

    async def test_process_direct_responses(self):
        pass

    async def test_get_direct_responses(self):
        pass

    async def test_message_handler(self):
        pass
