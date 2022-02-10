import aioredis
import asyncio
import aiohttp
from more_itertools import side_effect
import msgpack
import string

from asynctest import TestCase as AsyncTestCase, mock as async_mock, PropertyMock
from pathlib import Path
from time import time

from .. import service as test_module
from ..service import RedisHandler, main

test_msg_a = (
    None,
    msgpack.packb(
        {
            b"headers": {b"content-type": b"test"},
            b"endpoint": b"http://localhost:9000",
            b"payload": (string.digits + string.ascii_letters).encode(encoding="utf-8"),
        }
    ),
)
test_msg_b = (
    None,
    msgpack.packb(
        {
            b"headers": {b"content-type": b"test1"},
            b"endpoint": b"http://localhost:9000",
            b"payload": (string.digits + string.ascii_letters).encode(encoding="utf-8"),
        }
    ),
)
test_msg_c = (
    None,
    msgpack.packb(
        {
            b"headers": {b"content-type": b"test1"},
            b"endpoint": b"http://localhost:9000",
            b"payload": (string.digits + string.ascii_letters).encode(encoding="utf-8"),
        }
    ),
)
test_msg_d = (
    None,
    msgpack.packb(
        {
            b"headers": {b"content-type": b"test1"},
            b"endpoint": b"http://localhost:9000",
            b"payload": (string.digits + string.ascii_letters).encode(encoding="utf-8"),
            b"retries": 6,
        }
    ),
)
test_msg_e = (
    None,
    msgpack.packb(
        {
            b"headers": {b"content-type": b"test1"},
            b"endpoint": b"http://localhost:9000",
            b"payload": (string.digits + string.ascii_letters).encode(encoding="utf-8"),
            b"retry_time": int(time()),
        }
    ),
)
test_msg_err_a = (None, msgpack.packb(["invalid", "list", "require", "dict"]))
test_msg_err_b = (
    None,
    msgpack.packb(
        {
            "headers": {b"content-type": b"test1"},
            b"payload": (string.digits + string.ascii_letters).encode(encoding="utf-8"),
        }
    ),
)
test_msg_err_c = (
    None,
    msgpack.packb(
        {
            b"headers": {b"content-type": b"test1"},
            "endpoint": b"http://localhost:9000",
            b"payload": (string.digits + string.ascii_letters).encode(encoding="utf-8"),
            b"retries": 6,
        }
    ),
)
test_msg_err_d = (
    None,
    msgpack.packb(
        {
            b"headers": {b"content-type": b"test1"},
            b"endpoint": b"ws://localhost:9000",
            "payload": (string.digits + string.ascii_letters).encode(encoding="utf-8"),
        }
    ),
)
test_msg_err_e = (
    None,
    msgpack.packb(
        {
            b"headers": {b"content-type": b"test1"},
            b"endpoint": b"ws://localhost:9000",
            b"payload": (string.digits + string.ascii_letters).encode(encoding="utf-8"),
        }
    ),
)


class TestRedisHandler(AsyncTestCase):
    async def test_main(self):
        RedisHandler.RUNNING = PropertyMock(side_effect=[True, True, False])
        with async_mock.patch.object(
            test_module.aioredis,
            "from_url",
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
        with async_mock.patch.object(
            test_module.aioredis,
            "from_url",
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
        ), async_mock.patch.object(
            test_module.aioredis,
            "from_url",
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
                side_effect=[
                    aiohttp.ClientError,
                    asyncio.TimeoutError,
                    async_mock.MagicMock(status=400),
                ]
            ),
        ), async_mock.patch.object(
            test_module.aioredis,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            RedisHandler.RUNNING = PropertyMock(
                side_effect=[True, True, True, True, True, True, True, True, False]
            )
            mock_redis.blpop = async_mock.CoroutineMock(
                side_effect=[
                    aioredis.RedisError,
                    test_msg_a,
                    test_msg_b,
                    test_msg_d,
                    test_msg_err_a,
                    test_msg_err_b,
                    test_msg_err_c,
                    test_msg_err_d,
                    test_msg_err_e,
                ]
            )
            mock_redis.rpush = async_mock.CoroutineMock()
            mock_redis.zadd = async_mock.CoroutineMock(
                side_effect=[aioredis.RedisError, None, None]
            )
            service = RedisHandler("test", "acapy")
            service.redis = mock_redis
            await service.process_delivery()

    async def test_process_retries_a(self):
        with async_mock.patch.object(
            test_module.aioredis,
            "from_url",
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
        with async_mock.patch.object(
            test_module.aioredis,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            RedisHandler.RUNNING_RETRY = PropertyMock(side_effect=[True, False])
            mock_redis.zrangebyscore = async_mock.CoroutineMock(
                side_effect=[aioredis.RedisError, [test_msg_e, test_msg_e, test_msg_e]]
            )
            mock_redis.zrem = async_mock.CoroutineMock(
                side_effect=[0, aioredis.RedisError, test_msg_e, 0]
            )
            mock_redis.rpush = async_mock.CoroutineMock(
                side_effect=[aioredis.RedisError, None]
            )
            service = RedisHandler("test", "acapy")
            service.retry_timedelay_s = 0.1
            service.redis = mock_redis
            await service.process_retries()
