import os
import string

import aioredis
from asynctest import TestCase as AsyncTestCase, mock as async_mock
import msgpack
import pytest

from .....config.settings import Settings
from .....core.in_memory.profile import InMemoryProfile

from .. import redis as test_module
from ..base import OutboundQueueConfigurationError, OutboundQueueError
from ..redis import RedisOutboundQueue


ENDPOINT = "http://localhost:9000"
KEYNAME = "acapy.redis_outbound_transport"

REDIS_CONF = os.environ.get("TEST_REDIS_CONFIG", None)


class TestRedisOutbound(AsyncTestCase):
    def setUp(self):
        self.session = InMemoryProfile.test_session()
        self.profile = self.session.profile
        self.context = self.profile.context

    async def test_init(self):
        self.profile.settings["transport.outbound_queue"] = "connection"
        with async_mock.patch.object(
            test_module.aioredis,
            "from_url",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    blpop=async_mock.CoroutineMock(),
                    rpush=async_mock.CoroutineMock(),
                    ping=async_mock.CoroutineMock(),
                )
            ),
        ) as mock_redis:
            queue = RedisOutboundQueue(self.profile)
            queue.redis = mock_redis
            queue.prefix == "acapy"
            queue.connection = "connection"
            assert str(queue)
            await queue.start()

    def test_init_x(self):
        with pytest.raises(OutboundQueueConfigurationError):
            RedisOutboundQueue(self.profile)

    async def test_enqueue_message_str(self):
        self.profile.settings["transport.outbound_queue"] = "connection"
        with async_mock.patch.object(
            test_module.aioredis,
            "from_url",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    blpop=async_mock.CoroutineMock(),
                    rpush=async_mock.CoroutineMock(),
                    ping=async_mock.CoroutineMock(),
                )
            ),
        ) as mock_redis:
            queue = RedisOutboundQueue(self.profile)
            queue.redis = mock_redis
            await queue.start()
            await queue.enqueue_message(
                payload=string.ascii_letters + string.digits,
                endpoint=ENDPOINT,
            )
            message = msgpack.packb(
                {
                    "headers": {"Content-Type": "application/json"},
                    "endpoint": ENDPOINT,
                    "payload": (string.ascii_letters + string.digits),
                }
            )
            mock_redis.return_value.rpush.assert_called_once_with(
                "acapy.outbound_transport", message
            )

    async def test_enqueue_message_bytes(self):
        self.profile.settings["plugin_config"] = {
            "redis_outbound_queue": {
                "connection": "connection",
                "prefix": "acapy",
            }
        }
        with async_mock.patch.object(
            test_module.aioredis,
            "from_url",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    blpop=async_mock.CoroutineMock(),
                    rpush=async_mock.CoroutineMock(),
                    ping=async_mock.CoroutineMock(),
                )
            ),
        ) as mock_redis:
            queue = RedisOutboundQueue(self.profile)
            queue.redis = mock_redis
            bytes_payload = bytes(range(0, 256))
            await queue.start()
            await queue.enqueue_message(
                payload=bytes_payload,
                endpoint=ENDPOINT,
            )
            message = msgpack.packb(
                {
                    "headers": {"Content-Type": "application/ssi-agent-wire"},
                    "endpoint": ENDPOINT,
                    "payload": bytes_payload,
                }
            )
            mock_redis.return_value.rpush.assert_called_once_with(
                "acapy.outbound_transport", message
            )

    async def test_enqueue_message_x_redis_error(self):
        self.profile.settings["transport.outbound_queue"] = "connection"
        with async_mock.patch.object(
            test_module.aioredis,
            "from_url",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    blpop=async_mock.CoroutineMock(),
                    rpush=async_mock.CoroutineMock(
                        side_effect=[aioredis.RedisError, None]
                    ),
                    ping=async_mock.CoroutineMock(),
                )
            ),
        ) as mock_redis:
            queue = RedisOutboundQueue(self.profile)
            queue.redis = mock_redis
            await queue.start()
            await queue.enqueue_message(payload="", endpoint=ENDPOINT)

    async def test_enqueue_message_x_no_endpoint(self):
        self.profile.settings["transport.outbound_queue"] = "connection"
        with async_mock.patch.object(
            test_module.aioredis,
            "from_url",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    blpop=async_mock.CoroutineMock(),
                    rpush=async_mock.CoroutineMock(
                        side_effect=[aioredis.RedisError, None]
                    ),
                    ping=async_mock.CoroutineMock(),
                )
            ),
        ) as mock_redis:
            queue = RedisOutboundQueue(self.profile)
            queue.redis = mock_redis
            await queue.start()
            with pytest.raises(OutboundQueueError):
                await queue.enqueue_message(payload="", endpoint=None)
