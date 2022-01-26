import asyncio
import aioredis
import msgpack
import pytest
import random
import string

from asynctest import TestCase as AsyncTestCase, mock as async_mock, PropertyMock
from collections import Counter

from .. import service as test_module
from ..service import RedisHandler


class TestKafkaHandler(AsyncTestCase):
    def setUp(self):
        self.host = "test"
        self.prefix = "acapy"

    async def test_init(self):
        with async_mock.patch(
            "aioredis.ConnectionPool.from_url",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aioredis.Redis",
            async_mock.MagicMock(),
        ) as mock_redis:
            queue = RedisHandler()
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
