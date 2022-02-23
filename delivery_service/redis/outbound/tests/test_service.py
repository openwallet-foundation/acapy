import asyncio
import aiohttp
import msgpack
import redis
import string
import uvicorn

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
        RedisHandler.running = PropertyMock(side_effect=[True, True, False])
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis, async_mock.patch.object(
            RedisHandler, "process_delivery", autospec=True
        ), async_mock.patch.object(
            RedisHandler, "process_retries", autospec=True
        ), async_mock.patch.object(
            Path, "open", async_mock.MagicMock()
        ), async_mock.patch.object(
            uvicorn, "run", async_mock.MagicMock()
        ):
            main(
                [
                    "-oq",
                    "test",
                    "--endpoint-transport",
                    "0.0.0.0",
                    "8080",
                    "--endpoint-api-key",
                    "test123",
                ]
            )

    async def test_main_x(self):
        with self.assertRaises(SystemExit):
            main([])

        with self.assertRaises(SystemExit):
            main(
                [
                    "-oq",
                    "test",
                ]
            )
        with self.assertRaises(SystemExit):
            main(
                [
                    "-oq",
                    "test",
                    "--endpoint-transport",
                    "0.0.0.0",
                    "8081",
                ]
            )
        sentinel = PropertyMock(return_value=False)
        RedisHandler.running = sentinel
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(
                ping=async_mock.MagicMock(side_effect=redis.exceptions.RedisError)
            ),
        ) as mock_redis, async_mock.patch.object(
            RedisHandler, "process_delivery", autospec=True
        ), async_mock.patch.object(
            RedisHandler, "process_retries", autospec=True
        ), async_mock.patch.object(
            Path, "open", async_mock.MagicMock()
        ), async_mock.patch.object(
            uvicorn, "run", async_mock.MagicMock()
        ):
            main(
                [
                    "-oq",
                    "test",
                    "--endpoint-transport",
                    "0.0.0.0",
                    "8080",
                    "--endpoint-api-key",
                    "test123",
                ]
            )

    async def test_process_delivery(self):
        with async_mock.patch.object(
            aiohttp.ClientSession,
            "post",
            async_mock.CoroutineMock(return_value=async_mock.MagicMock(status=200)),
        ), async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis, async_mock.patch.object(
            RedisHandler, "process_retries", async_mock.CoroutineMock()
        ):
            RedisHandler.running = PropertyMock(
                side_effect=[True, True, True, True, False]
            )
            mock_redis.blpop = async_mock.MagicMock(
                side_effect=[
                    test_msg_a,
                    test_msg_b,
                    test_msg_c,
                    test_msg_d,
                ]
            )
            mock_redis.rpush = async_mock.MagicMock()
            mock_redis.zadd = async_mock.MagicMock()
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
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            RedisHandler.running = PropertyMock(
                side_effect=[True, True, True, True, True, True, True, True, False]
            )
            mock_redis.blpop = async_mock.MagicMock(
                side_effect=[
                    test_module.RedisError,
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
            mock_redis.rpush = async_mock.MagicMock()
            mock_redis.zadd = async_mock.MagicMock(
                side_effect=[test_module.RedisError, None, None]
            )
            service = RedisHandler("test", "acapy")
            service.redis = mock_redis
            await service.process_delivery()

    async def test_process_retries_a(self):
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            RedisHandler.running = PropertyMock(side_effect=[True, True, True, False])
            mock_redis.zrangebyscore = async_mock.MagicMock(
                side_effect=[
                    test_msg_e,
                    test_msg_e,
                    None,
                ]
            )
            mock_redis.zrem = async_mock.MagicMock(return_value=1)
            mock_redis.rpush = async_mock.MagicMock()
            service = RedisHandler("test", "acapy")
            service.retry_timedelay_s = 0.1
            service.redis = mock_redis
            await service.process_retries()

    async def test_process_retries_b(self):
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            RedisHandler.running = PropertyMock(side_effect=[True, False])
            mock_redis.zrangebyscore = async_mock.MagicMock(
                side_effect=[
                    test_module.RedisError,
                    [test_msg_e, test_msg_e, test_msg_e],
                ]
            )
            mock_redis.zrem = async_mock.MagicMock(
                side_effect=[0, test_module.RedisError, test_msg_e, 0]
            )
            mock_redis.rpush = async_mock.MagicMock(
                side_effect=[test_module.RedisError, None]
            )
            service = RedisHandler("test", "acapy")
            service.retry_timedelay_s = 0.1
            service.redis = mock_redis
            await service.process_retries()

    def test_status_live(self):
        test_module.API_KEY = "test1234"
        test_module.handler = async_mock.MagicMock(
            is_running=async_mock.MagicMock(return_value=False)
        )
        assert test_module.status_live(api_key="test1234") == {"alive": False}
        test_module.handler = async_mock.MagicMock(
            is_running=async_mock.MagicMock(return_value=True)
        )
        assert test_module.status_live(api_key="test1234") == {"alive": True}

    def test_status_ready(self):
        test_module.API_KEY = "test1234"
        test_module.handler = async_mock.MagicMock(ready=False)
        assert test_module.status_ready(api_key="test1234") == {"ready": False}
        test_module.handler = async_mock.MagicMock(ready=True)
        assert test_module.status_ready(api_key="test1234") == {"ready": True}

    def test_is_running(self):
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            sentinel = PropertyMock(return_value=True)
            RedisHandler.running = sentinel
            service = RedisHandler("test", "acapy")
            mock_redis = async_mock.MagicMock(ping=async_mock.MagicMock())
            service.redis = mock_redis
            service.running = True
            assert service.is_running()
            sentinel = PropertyMock(return_value=False)
            RedisHandler.running = sentinel
            service = RedisHandler("test", "acapy")
            mock_redis = async_mock.MagicMock(ping=async_mock.MagicMock())
            service.redis = mock_redis
            service.running = False
            assert not service.is_running()
            sentinel = PropertyMock(return_value=True)
            RedisHandler.running = sentinel
            service = RedisHandler("test", "acapy")
            mock_redis = async_mock.MagicMock(
                ping=async_mock.MagicMock(side_effect=redis.exceptions.RedisError)
            )
            service.redis = mock_redis
            service.running = True
            assert not service.is_running()
