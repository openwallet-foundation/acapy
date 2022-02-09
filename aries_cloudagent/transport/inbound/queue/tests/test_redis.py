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

from .. import redis as test_module
from ..base import InboundQueueConfigurationError, InboundQueueError
from ..redis import RedisInboundQueue


ENDPOINT = "http://localhost:9000"
KEYNAME = "acapy.redis_inbound_transport"

REDIS_CONF = os.environ.get("TEST_REDIS_CONFIG", None)


test_msg_a = (
    None,
    msgpack.packb(
        {
            "host": "test1",
            "remote": "http://localhost:9000",
            "data": (string.digits + string.ascii_letters),
            "transport_type": "ws",
        }
    ),
)
test_msg_b = (
    None,
    msgpack.packb(
        {
            "host": "test2",
            "remote": "http://localhost:9000",
            "data": (string.digits + string.ascii_letters),
            "txn_id": "test123",
            "transport_type": "http",
        }
    ),
)
test_msg_c = (
    None,
    msgpack.packb(
        {
            "host": "test2",
            "remote": "http://localhost:9000",
            "data": (string.digits + string.ascii_letters),
            "txn_id": "test123",
            "transport_type": "ws",
        }
    ),
)
test_msg_d = (
    None,
    msgpack.packb(
        """{
        "host": "test2",
        "remote": "http://localhost:9000",
        "data": (string.digits + string.ascii_letters),
        "txn_id": "test123",
        "transport_type": "http",
    }""".encode(
            "utf-8"
        )
    ),
)


class TestRedisInbound(AsyncTestCase):
    def setUp(self):
        self.session = InMemoryProfile.test_session()
        self.profile = self.session.profile
        self.context = self.profile.context

    async def test_init(self):
        self.profile.settings["transport.inbound_queue"] = "connection"
        with async_mock.patch(
            "aioredis.from_url",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aioredis.ConnectionPool",
            async_mock.MagicMock(),
        ):
            queue = RedisInboundQueue(self.profile)
            queue.prefix == "acapy"
            queue.connection = "connection"
            assert str(queue)
            await queue.start_queue()

    def test_init_x(self):
        with pytest.raises(InboundQueueConfigurationError):
            RedisInboundQueue(self.profile)

    async def test_receive_message(self):
        self.profile.settings["transport.inbound_queue"] = "connection"
        mock_inbound_mgr = async_mock.MagicMock(
            create_session=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    receive=async_mock.CoroutineMock(),
                    profile=self.profile,
                ),
            ),
        )
        with async_mock.patch.object(
            test_module.aioredis,
            "from_url",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    blpop=async_mock.CoroutineMock(
                        side_effect=[test_msg_a, test_msg_a]
                    ),
                    rpush=async_mock.CoroutineMock(),
                )
            ),
        ) as mock_redis:
            self.context.injector.bind_instance(
                InboundTransportManager, mock_inbound_mgr
            )
            sentinel = PropertyMock(side_effect=[True, True, False])
            RedisInboundQueue.RUNNING = sentinel
            queue = RedisInboundQueue(self.profile)
            queue.redis = mock_redis
            await queue.start_queue()
            await queue.receive_messages()
        assert mock_redis.return_value.blpop.call_count == 2
        assert mock_redis.return_value.rpush.call_count == 0

    async def test_receive_message_x(self):
        self.profile.settings["transport.inbound_queue"] = "connection"
        mock_inbound_mgr = async_mock.MagicMock(
            create_session=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    receive=async_mock.CoroutineMock(),
                    profile=self.profile,
                ),
            ),
        )
        with async_mock.patch.object(
            test_module.aioredis,
            "from_url",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    blpop=async_mock.CoroutineMock(side_effect=aioredis.RedisError),
                    rpush=async_mock.CoroutineMock(),
                )
            ),
        ) as mock_redis, async_mock.patch.object(
            test_module.asyncio, "sleep", async_mock.CoroutineMock()
        ) as mock_sleep:
            self.context.injector.bind_instance(
                InboundTransportManager, mock_inbound_mgr
            )
            sentinel = PropertyMock(side_effect=[True, False])
            RedisInboundQueue.RUNNING = sentinel
            queue = RedisInboundQueue(self.profile)
            queue.redis = mock_redis
            await queue.start_queue()
            with self.assertRaises(InboundQueueError):
                await queue.receive_messages()

    async def test_receive_message_direct_response_a(self):
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
                    profile=self.profile,
                )
            ),
        )
        with async_mock.patch.object(
            test_module.aioredis,
            "from_url",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    blpop=async_mock.CoroutineMock(
                        side_effect=[test_msg_b, test_msg_b, test_msg_c]
                    ),
                    rpush=async_mock.CoroutineMock(),
                )
            ),
        ) as mock_redis:
            self.context.injector.bind_instance(
                InboundTransportManager, mock_inbound_mgr
            )
            sentinel = PropertyMock(side_effect=[True, True, True, False])
            RedisInboundQueue.RUNNING = sentinel
            queue = RedisInboundQueue(self.profile)
            queue.redis = mock_redis
            await queue.start_queue()
            await queue.receive_messages()
        assert mock_redis.return_value.blpop.call_count == 3
        assert mock_redis.return_value.rpush.call_count == 3

    async def test_receive_message_direct_response_b(self):
        self.profile.settings["transport.inbound_queue"] = "connection"
        self.profile.settings["emit_new_didcomm_mime_type"] = True
        mock_inbound_mgr = async_mock.MagicMock(
            create_session=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    receive=async_mock.CoroutineMock(),
                    wait_response=async_mock.CoroutineMock(
                        side_effect=[b"test_response"]
                    ),
                    profile=self.profile,
                )
            ),
        )
        with async_mock.patch.object(
            test_module.aioredis,
            "from_url",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    blpop=async_mock.CoroutineMock(
                        side_effect=[test_msg_b, test_msg_d]
                    ),
                    rpush=async_mock.CoroutineMock(),
                )
            ),
        ) as mock_redis:
            self.context.injector.bind_instance(
                InboundTransportManager, mock_inbound_mgr
            )
            sentinel = PropertyMock(side_effect=[True, True, False])
            RedisInboundQueue.RUNNING = sentinel
            queue = RedisInboundQueue(self.profile)
            queue.redis = mock_redis
            await queue.start_queue()
            await queue.receive_messages()

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
                    profile=self.profile,
                )
            ),
        )
        with async_mock.patch.object(
            test_module.aioredis,
            "from_url",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    blpop=async_mock.CoroutineMock(side_effect=[test_msg_b]),
                    rpush=async_mock.CoroutineMock(side_effect=[aioredis.RedisError]),
                )
            ),
        ) as mock_redis:
            self.context.injector.bind_instance(
                InboundTransportManager, mock_inbound_mgr
            )
            sentinel = PropertyMock(side_effect=[True, False])
            RedisInboundQueue.RUNNING = sentinel
            queue = RedisInboundQueue(self.profile)
            queue.redis = mock_redis
            await queue.start_queue()
            with self.assertRaises(InboundQueueError):
                await queue.receive_messages()
