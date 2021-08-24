import os
import string

import aioredis
from asynctest import mock as async_mock
import msgpack
import pytest

from .....config.settings import Settings
from ..base import OutboundQueueConfigurationError, OutboundQueueError
from ..redis import RedisOutboundQueue


ENDPOINT = "http://localhost:9000"
KEYNAME = "acapy.outbound_transport"

REDIS_CONF = os.environ.get("TEST_REDIS_CONFIG", None)


@pytest.fixture
async def mock_redis():
    with async_mock.patch(
        "aioredis.ConnectionPool.from_url", async_mock.MagicMock()
    ), async_mock.patch("aioredis.Redis", async_mock.MagicMock()):
        yield


@pytest.fixture
def settings():
    def _settings_factory(connection=None, prefix=None):
        return Settings(
            values={
                "plugin_config": {
                    RedisOutboundQueue.config_key: {
                        "connection": connection or "connection",
                        "prefix": prefix or "acapy",
                    }
                }
            }
        )

    yield _settings_factory


@pytest.fixture
def queue(settings, mock_redis):
    yield RedisOutboundQueue(settings())


@pytest.fixture
def mock_rpush(queue):
    pushed = []

    async def _mock_rpush(key, message):
        pushed.append((key, message))

    queue.redis.rpush = _mock_rpush
    yield pushed


def test_init(mock_redis, settings):
    q = RedisOutboundQueue(settings())
    q.prefix == "acapy"
    q.connection = "connection"
    assert str(q)


def test_init_x(mock_redis, settings):
    with pytest.raises(OutboundQueueConfigurationError):
        RedisOutboundQueue(Settings())


@pytest.mark.asyncio
async def test_enqueue_message_str(queue, mock_rpush):
    await queue.enqueue_message(
        payload=string.ascii_letters + string.digits,
        endpoint=ENDPOINT,
    )
    [(key, message)] = mock_rpush
    assert (
        msgpack.unpackb(message).get("headers", {}).get("Content-Type")
        == "application/json"
    )


@pytest.mark.asyncio
async def test_enqueue_message_bytes(queue, mock_rpush):
    await queue.enqueue_message(
        payload=bytes(range(0, 256)),
        endpoint=ENDPOINT,
    )
    [(key, message)] = mock_rpush
    assert (
        msgpack.unpackb(message).get("headers", {}).get("Content-Type")
        == "application/ssi-agent-wire"
    )


@pytest.mark.asyncio
async def test_enqueue_message_x_redis_error(queue):
    queue.redis.rpush = async_mock.CoroutineMock(side_effect=aioredis.RedisError)
    with pytest.raises(OutboundQueueError):
        await queue.enqueue_message(payload="", endpoint=ENDPOINT)


@pytest.mark.asyncio
async def test_enqueue_message_x_no_endpoint(queue):
    queue.redis.rpush = async_mock.CoroutineMock(side_effect=aioredis.RedisError)
    with pytest.raises(OutboundQueueError):
        await queue.enqueue_message(payload="", endpoint=None)
