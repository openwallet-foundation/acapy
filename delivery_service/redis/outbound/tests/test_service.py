import aioredis
import aiohttp
import msgpack
import pytest
import random
import string

from asynctest import TestCase as AsyncTestCase, mock as async_mock, PropertyMock
from pathlib import Path
from time import time

from .. import service as test_module
from ..service import RedisHandler, main

test_msg_a = msgpack.packb(
    {
        "headers": {"content-type": "test"},
        "endpoint": "http://localhost:9000",
        "payload": (string.digits + string.ascii_letters).encode(encoding="utf-8"),
    }
)
test_msg_b = msgpack.packb(
    {
        "headers": {"content-type": b"test1"},
        "endpoint": "http://localhost:9000",
        "payload": (string.digits + string.ascii_letters).encode(encoding="utf-8"),
    }
)
test_msg_c = msgpack.packb(
    {
        "headers": {"content-type": "test1"},
        "endpoint": "http://localhost:9000",
        "payload": (bytes(range(0, 256))),
    }
)
test_msg_d = msgpack.packb(
    {
        "headers": {"content-type": "test1"},
        "endpoint": "http://localhost:9000",
        "payload": (bytes(range(0, 256))),
        "retries": 6,
    }
)
test_msg_e = msgpack.packb(
    {
        "headers": {"content-type": "test1"},
        "endpoint": "http://localhost:9000",
        "payload": (bytes(range(0, 256))),
        "retry_time": int(time()),
    }
)
test_msg_err_a = msgpack.packb(["invalid", "list", "require", "dict"])
test_msg_err_b = msgpack.packb(
    {
        "headers": {"content-type": "test1"},
        "payload": (bytes(range(0, 256))),
    }
)
test_msg_err_c = msgpack.packb(
    {
        "headers": {"content-type": "test1"},
        "endpoint": "http://localhost:9000",
        "payload": (bytes(range(0, 256))),
        "retries": 6,
    }
)
test_msg_err_d = msgpack.packb(
    {
        "headers": {"content-type": "test1"},
        "endpoint": "ws://localhost:9000",
        "payload": (bytes(range(0, 256))),
    }
)
test_msg_err_e = msgpack.packb(
    {
        "headers": {"content-type": "test1"},
        "endpoint": "http://localhost:9000",
    }
)


class TestRedisHandler(AsyncTestCase):
    async def test_main(self):
        RedisHandler.RUNNING = PropertyMock(side_effect=[True, True, False])
        with async_mock.patch(
            "aioredis.ConnectionPool.from_url",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aioredis.Redis",
            async_mock.MagicMock(),
        ) as mock_redis, async_mock.patch.object(
            RedisHandler, "process_delivery", autospec=True
        ), async_mock.patch.object(
            RedisHandler, "process_retries", autospec=True
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

    async def test_main_plugin_config(self):
        RedisHandler.RUNNING = PropertyMock(side_effect=[True, True, False])
        with async_mock.patch(
            "aioredis.ConnectionPool.from_url",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aioredis.Redis",
            async_mock.MagicMock(),
        ) as mock_redis, async_mock.patch.object(
            RedisHandler, "process_delivery", autospec=True
        ), async_mock.patch.object(
            RedisHandler, "process_retries", autospec=True
        ), async_mock.patch.object(
            test_module.yaml,
            "safe_load",
            async_mock.MagicMock(
                return_value={"redis_outbound_queue": {"connection": "test"}}
            ),
        ), async_mock.patch.object(
            Path, "open", async_mock.MagicMock()
        ), async_mock.patch(
            "builtins.open", async_mock.MagicMock()
        ) as mock_open:
            await main(
                [
                    "--plugin-config",
                    "test_yaml_path.yml",
                ]
            )

    async def test_process_delivery(self):
        with async_mock.patch.object(
            aiohttp.ClientSession,
            "post",
            async_mock.CoroutineMock(return_value=async_mock.MagicMock(status=200)),
        ), async_mock.patch(
            "aioredis.ConnectionPool.from_url",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aioredis.Redis",
            async_mock.MagicMock(),
        ) as mock_redis, async_mock.patch.object(
            RedisHandler, "process_retries", async_mock.CoroutineMock()
        ):
            RedisHandler.RUNNING = PropertyMock(
                side_effect=[True, True, True, True, False]
            )
            mock_redis.blpop = async_mock.CoroutineMock(
                side_effect=[
                    test_msg_a,
                    test_msg_b,
                    test_msg_c,
                    test_msg_d,
                ]
            )
            mock_redis.rpush = async_mock.CoroutineMock()
            mock_redis.zadd = async_mock.CoroutineMock()
            service = RedisHandler("test", "acapy")
            service.redis = mock_redis
            await service.process_delivery()

    async def test_process_delivery_x(self):
        with async_mock.patch.object(
            aiohttp.ClientSession,
            "post",
            async_mock.CoroutineMock(
                side_effect=[aiohttp.ClientError, async_mock.MagicMock(status=400)]
            ),
        ), async_mock.patch(
            "aioredis.ConnectionPool.from_url",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aioredis.Redis",
            async_mock.MagicMock(),
        ) as mock_redis:
            RedisHandler.RUNNING = PropertyMock(
                side_effect=[True, True, True, True, True, True, False]
            )
            mock_redis.blpop = async_mock.CoroutineMock(
                side_effect=[
                    test_msg_a,
                    test_msg_err_a,
                    test_msg_err_b,
                    test_msg_err_c,
                    test_msg_err_d,
                    test_msg_err_e,
                ]
            )
            mock_redis.rpush = async_mock.CoroutineMock()
            mock_redis.zadd = async_mock.CoroutineMock()
            service = RedisHandler("test", "acapy")
            service.redis = mock_redis
            await service.process_delivery()

    async def test_process_retries_a(self):
        with async_mock.patch(
            "aioredis.ConnectionPool.from_url",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aioredis.Redis",
            async_mock.MagicMock(),
        ) as mock_redis:
            RedisHandler.RUNNING_RETRY = PropertyMock(
                side_effect=[True, True, True, False]
            )
            mock_redis.zrangebyscore = async_mock.CoroutineMock(
                side_effect=[
                    test_msg_e,
                    test_msg_e,
                    None,
                ]
            )
            mock_redis.zrem = async_mock.CoroutineMock(return_value=1)
            mock_redis.rpush = async_mock.CoroutineMock()
            service = RedisHandler("test", "acapy")
            service.retry_timedelay_s = 0.1
            service.redis = mock_redis
            await service.process_retries()

    async def test_process_retries_b(self):
        with async_mock.patch(
            "aioredis.ConnectionPool.from_url",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aioredis.Redis",
            async_mock.MagicMock(),
        ) as mock_redis:
            RedisHandler.RUNNING_RETRY = PropertyMock(side_effect=[True, False])
            mock_redis.zrangebyscore = async_mock.CoroutineMock(
                side_effect=[
                    test_msg_e,
                ]
            )
            mock_redis.zrem = async_mock.CoroutineMock(return_value=0)
            mock_redis.rpush = async_mock.CoroutineMock()
            service = RedisHandler("test", "acapy")
            service.retry_timedelay_s = 0.1
            service.redis = mock_redis
            await service.process_retries()
