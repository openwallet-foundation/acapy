import asyncio
import base64
import msgpack
import os
import pytest
import string

from asynctest import TestCase as AsyncTestCase, mock as async_mock
import unittest
from aiohttp import web
import aioredis

from .....config.injection_context import InjectionContext
from .....utils.stats import Collector

from ....outbound.message import OutboundMessage
from ....wire_format import JsonWireFormat

from ...base import OutboundTransportError
from ..base import OutboundQueueError
from ..redis import RedisOutboundQueue


ENDPOINT = "http://localhost:9000"
KEYNAME = "acapy.outbound_transport"

REDIS_CONF = os.environ.get("TEST_REDIS_CONFIG", None)


@unittest.skipUnless(
    REDIS_CONF,
    ("Redis conf not defined via OS environment variable TEST_REDIS_CONFIG"),
)
class TestRedisOutboundQueue(AsyncTestCase):
    async def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.transport = RedisOutboundQueue(
            connection=REDIS_CONF,
        )
        self.redis = await aioredis.create_redis_pool(
            REDIS_CONF,
            minsize=5,
            maxsize=10,
            loop=self.loop,
        )
        await self.redis.delete(KEYNAME)

    async def tearDown(self):
        await self.redis.delete(KEYNAME)
        self.redis.close()
        await self.redis.wait_closed()

    async def receive_message(self):
        message = await self.redis.blpop(KEYNAME)
        return message[1]

    async def test_enqueue_message_str(self):
        transmitted_str = string.ascii_letters + string.digits
        async with self.transport:
            await self.transport.enqueue_message(
                payload=transmitted_str,
                endpoint=ENDPOINT,
            )
        message = await self.receive_message()
        payload = msgpack.unpackb(message).get("payload")
        self.assertEqual(payload, transmitted_str.encode())

    async def test_enqueue_message_bytes(self):
        transmitted_bytes = bytes(range(0, 256))
        async with self.transport:
            await self.transport.enqueue_message(
                payload=transmitted_bytes,
                endpoint=ENDPOINT,
            )
        message = await self.receive_message()
        payload = msgpack.unpackb(message).get("payload")
        self.assertEqual(payload, transmitted_bytes)

    async def test_redis_error_handled(self):
        transmitted_str = string.ascii_letters + string.digits
        async with self.transport:
            with unittest.mock.patch.object(
                self.transport.redis,
                "rpush",
                side_effect=aioredis.RedisError,
                new_callable=AsyncMock,
            ) as mock_rpush:
                with self.assertRaises(OutboundQueueError):
                    await self.transport.enqueue_message(
                        payload=transmitted_str,
                        endpoint=ENDPOINT,
                    )


class TestRedisConnection(AsyncTestCase):
    TEST_REDIS_ENDPOINT = "redis://test_redis_endpoint:6379"

    async def test_endpoint_goes_into_class(self):
        transport = RedisOutboundQueue(
            connection=TestRedisConnection.TEST_REDIS_ENDPOINT
        )
        assert str(transport)
        with async_mock.patch.object(
            aioredis, "create_redis_pool", async_mock.CoroutineMock()
        ) as mock_pool:
            mock_pool.return_value = async_mock.MagicMock(
                close=async_mock.MagicMock(),
                wait_closed=async_mock.CoroutineMock(),
            )
            async with transport:
                pass

        mock_pool.assert_called_once()
        self.assertEqual(
            mock_pool.call_args[0][0], TestRedisConnection.TEST_REDIS_ENDPOINT
        )

    async def test_outbound_aexit_x(self):
        transport = RedisOutboundQueue(
            connection=TestRedisConnection.TEST_REDIS_ENDPOINT
        )
        with unittest.mock.patch.object(
            aioredis, "create_redis_pool", new_callable=AsyncMock
        ) as mock_pool, unittest.mock.patch.object(
            transport.logger, "exception", autospec=True
        ) as mock_log_exc:
            mock_pool.return_value = async_mock.MagicMock(
                close=async_mock.MagicMock(),
                wait_closed=async_mock.CoroutineMock(),
            )
            try:
                async with transport:
                    raise ValueError("oops")
            except ValueError:
                pass

        mock_log_exc.assert_called_once()
        mock_pool.assert_called_once()
        self.assertEqual(
            mock_pool.call_args[0][0], TestRedisConnection.TEST_REDIS_ENDPOINT
        )

    async def test_enqueue(self):
        transport = RedisOutboundQueue(
            connection=TestRedisConnection.TEST_REDIS_ENDPOINT
        )

        with async_mock.patch.object(
            aioredis, "create_redis_pool", async_mock.CoroutineMock()
        ) as mock_pool:
            mock_pool.return_value = async_mock.MagicMock(
                close=async_mock.MagicMock(),
                wait_closed=async_mock.CoroutineMock(),
            )
            async with transport:
                with async_mock.patch.object(
                    transport.redis, "rpush", async_mock.CoroutineMock()
                ) as mock_redis_push:
                    await transport.enqueue_message("Hello", "localhost:8999")
                    await transport.enqueue_message(b"Hello", "localhost:8999")

    async def test_enqueue_push_x(self):
        transport = RedisOutboundQueue(
            connection=TestRedisConnection.TEST_REDIS_ENDPOINT
        )

        with async_mock.patch.object(
            aioredis, "create_redis_pool", async_mock.CoroutineMock()
        ) as mock_pool:
            mock_pool.return_value = async_mock.MagicMock(
                close=async_mock.MagicMock(),
                wait_closed=async_mock.CoroutineMock(),
            )
            async with transport:
                with async_mock.patch.object(
                    transport.redis, "rpush", async_mock.CoroutineMock()
                ) as mock_redis_push:
                    mock_redis_push.side_effect = aioredis.RedisError()
                    with self.assertRaises(OutboundQueueError):
                        await transport.enqueue_message("Hello", "localhost:8999")

    async def test_enqueue_no_endpoint_x(self):
        transport = RedisOutboundQueue(
            connection=TestRedisConnection.TEST_REDIS_ENDPOINT
        )

        with async_mock.patch.object(
            aioredis, "create_redis_pool", async_mock.CoroutineMock()
        ) as mock_pool:
            mock_pool.return_value = async_mock.MagicMock(
                close=async_mock.MagicMock(),
                wait_closed=async_mock.CoroutineMock(),
            )
            async with transport:
                with self.assertRaises(OutboundQueueError):  # cover exc
                    await transport.enqueue_message(None, None)


class AsyncMock(unittest.mock.MagicMock):
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)
