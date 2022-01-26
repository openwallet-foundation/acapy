import aioredis
import msgpack
import pytest
import random
import os
import string

from asynctest import TestCase as AsyncTestCase, mock as async_mock, PropertyMock

from .....config.settings import Settings
from .....core.in_memory.profile import InMemoryProfile

from ...manager import InboundTransportManager

from ..base import InboundQueueConfigurationError, InboundQueueError
from ..redis import RedisInboundQueue


ENDPOINT = "http://localhost:9000"
KEYNAME = "acapy.redis_inbound_transport"

REDIS_CONF = os.environ.get("TEST_REDIS_CONFIG", None)


def mock_blpop(response_reqd=False):
    if not response_reqd:
        return msgpack.packb(
            {
                "host": "test1",
                "remote": "http://localhost:9000",
                "data": (string.digits + string.ascii_letters).encode(encoding="utf-8"),
            }
        )
    else:
        index = round(random.random())
        if index == 0:
            return msgpack.packb(
                {
                    "host": "test2",
                    "remote": "http://localhost:9000",
                    "data": bytes(range(0, 256)),
                    "txn_id": "test123",
                    "transport_type": "http",
                }
            )
        else:
            return msgpack.packb(
                {
                    "host": "test2",
                    "remote": "http://localhost:9000",
                    "data": bytes(range(0, 256)),
                    "txn_id": "test123",
                    "transport_type": "ws",
                }
            )


def decode_func(value):
    return value.decode("utf-8")


class TestRedisInbound(AsyncTestCase):
    def setUp(self):
        self.session = InMemoryProfile.test_session()
        self.profile = self.session.profile
        self.context = self.profile.context

    async def test_init(self):
        self.profile.settings["transport.inbound_queue"] = "connection"
        with async_mock.patch(
            "aioredis.ConnectionPool.from_url",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aioredis.Redis",
            async_mock.MagicMock(),
        ):
            queue = RedisInboundQueue(self.profile)
            queue.prefix == "acapy"
            queue.connection = "connection"
            assert str(queue)
            await queue.start()

    def test_init_x(self):
        with pytest.raises(InboundQueueConfigurationError):
            RedisInboundQueue(self.profile)

    async def test_receive_message(self):
        self.profile.settings["transport.inbound_queue"] = "connection"
        mock_inbound_mgr = async_mock.MagicMock(
            create_session=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(receive=async_mock.CoroutineMock())
            ),
        )
        with async_mock.patch(
            "aioredis.ConnectionPool.from_url",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aioredis.Redis",
            async_mock.MagicMock(),
        ) as mock_redis:
            mock_redis.blpop = async_mock.CoroutineMock(return_value=mock_blpop())
            mock_redis.rpush = async_mock.CoroutineMock()
            self.context.injector.bind_instance(
                InboundTransportManager, mock_inbound_mgr
            )
            sentinel = PropertyMock(side_effect=[True, True, False])
            RedisInboundQueue.RUNNING = sentinel
            queue = RedisInboundQueue(self.profile)
            queue.redis = mock_redis
            await queue.start()
            await queue.receive_messages()
        assert mock_redis.blpop.call_count == 2
        assert mock_redis.rpush.call_count == 0

    async def test_receive_message_x(self):
        self.profile.settings["transport.inbound_queue"] = "connection"
        mock_inbound_mgr = async_mock.MagicMock(
            create_session=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(receive=async_mock.CoroutineMock())
            ),
        )
        with async_mock.patch(
            "aioredis.ConnectionPool.from_url",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aioredis.Redis",
            async_mock.MagicMock(),
        ) as mock_redis:
            mock_redis.blpop = async_mock.CoroutineMock(side_effect=aioredis.RedisError)
            mock_redis.rpush = async_mock.CoroutineMock()
            self.context.injector.bind_instance(
                InboundTransportManager, mock_inbound_mgr
            )
            sentinel = PropertyMock(side_effect=[True, False])
            RedisInboundQueue.RUNNING = sentinel
            queue = RedisInboundQueue(self.profile)
            queue.redis = mock_redis
            await queue.start()
            with self.assertRaises(InboundQueueError):
                await queue.receive_messages()

    async def test_receive_message_direct_response(self):
        self.profile.settings["plugin_config"] = {
            "redis_inbound_queue": {
                "connection": "connection",
                "prefix": "acapy",
            }
        }
        mock_inbound_mgr = async_mock.MagicMock(
            create_session=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    receive=async_mock.CoroutineMock(),
                    wait_response=async_mock.CoroutineMock(
                        side_effect=[b"test_response", "response", "response"]
                    ),
                )
            ),
        )
        with async_mock.patch(
            "aioredis.ConnectionPool.from_url",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aioredis.Redis",
            async_mock.MagicMock(),
        ) as mock_redis:
            mock_redis.blpop = async_mock.CoroutineMock(
                return_value=mock_blpop(response_reqd=True)
            )
            mock_redis.rpush = async_mock.CoroutineMock()
            self.context.injector.bind_instance(
                InboundTransportManager, mock_inbound_mgr
            )
            sentinel = PropertyMock(side_effect=[True, True, True, False])
            RedisInboundQueue.RUNNING = sentinel
            queue = RedisInboundQueue(self.profile)
            queue.redis = mock_redis
            await queue.start()
            await queue.receive_messages()
        assert mock_redis.blpop.call_count == 3
        assert mock_redis.rpush.call_count == 3

    async def test_receive_message_direct_response_x(self):
        self.profile.settings["plugin_config"] = {
            "redis_inbound_queue": {
                "connection": "connection",
                "prefix": "acapy",
            }
        }
        mock_inbound_mgr = async_mock.MagicMock(
            create_session=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    receive=async_mock.CoroutineMock(),
                    wait_response=async_mock.CoroutineMock(
                        side_effect=[b"test_response"]
                    ),
                )
            ),
        )
        with async_mock.patch(
            "aioredis.ConnectionPool.from_url",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aioredis.Redis",
            async_mock.MagicMock(),
        ) as mock_redis:
            mock_redis.blpop = async_mock.CoroutineMock(
                return_value=mock_blpop(response_reqd=True)
            )
            mock_redis.rpush = async_mock.CoroutineMock(side_effect=aioredis.RedisError)
            self.context.injector.bind_instance(
                InboundTransportManager, mock_inbound_mgr
            )
            sentinel = PropertyMock(side_effect=[True, False])
            RedisInboundQueue.RUNNING = sentinel
            queue = RedisInboundQueue(self.profile)
            queue.redis = mock_redis
            await queue.start()
            with self.assertRaises(InboundQueueError):
                await queue.receive_messages()
