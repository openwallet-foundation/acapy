import asyncio
import aioredis
import msgpack
import pytest
import random
import string

from asynctest import TestCase as AsyncTestCase, mock as async_mock, PropertyMock
from collections import Counter

from .. import service as test_module
from ..service import RedisHTTPHandler, RedisWSHandler


class TestRedisHTTPHandler(AsyncTestCase):
    def setUp(self):
        self.host = "test"
        self.prefix = "acapy"
        self.site_host = ""
        self.site_port = ""

    async def test_init(self):
        with async_mock.patch(
            "aioredis.ConnectionPool.from_url",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aioredis.Redis",
            async_mock.MagicMock(),
        ) as mock_redis:
            queue = RedisHTTPHandler()
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

class TestRedisWSHandler(AsyncTestCase):
    def setUp(self):
        self.host = "test"
        self.prefix = "acapy"
        self.site_host = ""
        self.site_port = ""

    async def test_init(self):
        with async_mock.patch(
            "aioredis.ConnectionPool.from_url",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aioredis.Redis",
            async_mock.MagicMock(),
        ) as mock_redis:
            queue = RedisWSHandler()
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
