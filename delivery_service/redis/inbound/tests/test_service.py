import aiohttp
from more_itertools import side_effect
import msgpack
import json
import redis
import uvicorn

from asynctest import TestCase as AsyncTestCase, mock as async_mock, PropertyMock
from pathlib import Path

from .. import service as test_module
from ..service import RedisHTTPHandler, RedisWSHandler, main

test_retry_msg_a = msgpack.packb(["invalid", "list", "require", "dict"])
test_retry_msg_b = msgpack.packb(
    {
        "response_data": (bytes(range(0, 256))),
    }
)
test_retry_msg_c = msgpack.packb(
    {
        "response_data": (bytes(range(0, 256))),
        "txn_id": "test123",
    }
)
test_retry_msg_d = msgpack.packb(
    {
        "txn_id": "test123",
    }
)


class TestRedisHTTPHandler(AsyncTestCase):
    async def test_main(self):
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis, async_mock.patch.object(
            RedisHTTPHandler, "start", async_mock.CoroutineMock()
        ), async_mock.patch.object(
            RedisHTTPHandler, "process_direct_responses", async_mock.CoroutineMock()
        ), async_mock.patch.object(
            Path, "open", async_mock.MagicMock()
        ), async_mock.patch.object(
            uvicorn, "run", async_mock.MagicMock()
        ):
            sentinel = PropertyMock(return_value=False)
            RedisHTTPHandler.running = sentinel
            main(
                [
                    "-iq",
                    "test",
                    "-iqt",
                    "http",
                    "0.0.0.0",
                    "8080",
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
                    "-iq",
                    "test",
                    "--endpoint-transport",
                    "0.0.0.0",
                    "8080",
                    "--endpoint-api-key",
                    "test123",
                ]
            )
        with self.assertRaises(SystemExit):
            main(
                [
                    "-iq",
                    "test",
                    "-iqt",
                    "invalid",
                    "0.0.0.0",
                    "8080",
                ]
            )
        with self.assertRaises(SystemExit):
            main(
                [
                    "-iq",
                    "test",
                    "-iqt",
                    "http",
                    "0.0.0.0",
                    "8080",
                    "--endpoint-transport",
                    "0.0.0.0",
                    "8081",
                ]
            )
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(
                ping=async_mock.MagicMock(side_effect=redis.exceptions.RedisError)
            ),
        ) as mock_redis, async_mock.patch.object(
            RedisHTTPHandler, "start", async_mock.CoroutineMock()
        ), async_mock.patch.object(
            RedisHTTPHandler, "process_direct_responses", async_mock.CoroutineMock()
        ), async_mock.patch.object(
            Path, "open", async_mock.MagicMock()
        ), async_mock.patch.object(
            uvicorn, "run", async_mock.MagicMock()
        ):
            main(
                [
                    "-iq",
                    "test",
                    "-iqt",
                    "http",
                    "0.0.0.0",
                    "8080",
                    "--endpoint-transport",
                    "0.0.0.0",
                    "8080",
                    "--endpoint-api-key",
                    "test123",
                ]
            )

    async def test_stop(self):
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis, async_mock.patch.object(
            test_module.web,
            "TCPSite",
            async_mock.MagicMock(stop=async_mock.CoroutineMock()),
        ) as mock_site:
            mock_redis.blpop = async_mock.MagicMock()
            mock_redis.rpush = async_mock.MagicMock()
            sentinel = PropertyMock(side_effect=[True, True, True, False])
            RedisHTTPHandler.running = sentinel
            service = RedisHTTPHandler("test", "acapy", "test", "8080")
            service.site = async_mock.MagicMock(stop=async_mock.CoroutineMock())
            service.redis = mock_redis
            await service.stop()

    async def test_start(self):
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis, async_mock.patch.object(
            test_module.web,
            "TCPSite",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    stop=async_mock.CoroutineMock(),
                    start=async_mock.CoroutineMock(),
                )
            ),
        ), async_mock.patch.object(
            test_module.web.AppRunner,
            "setup",
            async_mock.CoroutineMock(),
        ):
            mock_redis.blpop = async_mock.MagicMock()
            mock_redis.rpush = async_mock.MagicMock()
            sentinel = PropertyMock(side_effect=[True, True, True, False])
            RedisHTTPHandler.running = sentinel
            service = RedisHTTPHandler("test", "acapy", "test", "8080")
            service.redis = mock_redis
            await service.start()

    async def test_process_direct_response(self):
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            mock_redis.blpop = async_mock.MagicMock(
                side_effect=[
                    (None, test_retry_msg_a),
                    (None, test_retry_msg_b),
                    (None, test_retry_msg_c),
                    test_module.RedisError,
                    (None, test_retry_msg_d),
                ]
            )
            sentinel = PropertyMock(side_effect=[True, True, True, True, False])
            RedisHTTPHandler.running = sentinel
            service = RedisHTTPHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            service.redis = mock_redis
            assert service.direct_response_txn_request_map == {}
            await service.process_direct_responses()
            assert service.direct_response_txn_request_map != {}

    async def test_get_direct_response(self):
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            sentinel = PropertyMock(side_effect=[True, True, False])
            RedisHTTPHandler.running = sentinel
            service = RedisHTTPHandler("test", "acapy", "test", "8080")
            service.redis = mock_redis
            service.timedelay_s = 0.1
            service.direct_response_txn_request_map = {
                "txn_123": b"test",
                "txn_124": b"test2",
            }
            await service.get_direct_responses("txn_321")
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            sentinel = PropertyMock(side_effect=[True, False])
            RedisHTTPHandler.running = sentinel
            service = RedisHTTPHandler("test", "acapy", "test", "8080")
            service.redis = mock_redis
            service.timedelay_s = 0.1
            service.direct_response_txn_request_map = {
                "txn_123": b"test",
                "txn_124": b"test2",
            }
            await service.get_direct_responses("txn_123") == b"test"
            await service.get_direct_responses("txn_124") == b"test2"

    async def test_message_handler(self):
        mock_request = async_mock.MagicMock(
            headers={"content-type": "application/json"},
            text=async_mock.CoroutineMock(return_value=json.dumps({"test": "...."})),
            host="test",
            remote="test",
        )
        sentinel = PropertyMock(side_effect=[True, False])
        RedisHTTPHandler.running = sentinel
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            service = RedisHTTPHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            mock_redis.blpop = async_mock.MagicMock()
            mock_redis.rpush = async_mock.MagicMock()
            service.redis = mock_redis
            assert (await service.message_handler(mock_request)).status == 200
        with async_mock.patch.object(
            RedisHTTPHandler,
            "get_direct_responses",
            async_mock.CoroutineMock(
                return_value={"response": json.dumps({"test": "...."})}
            ),
        ), async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            service = RedisHTTPHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            mock_redis.blpop = async_mock.MagicMock()
            mock_redis.rpush = async_mock.MagicMock()
            service.redis = mock_redis
            mock_request = async_mock.MagicMock(
                headers={"content-type": "..."},
                read=async_mock.CoroutineMock(
                    return_value=json.dumps(
                        {"test": "....", "~transport": {"return_route": "..."}}
                    )
                ),
                host="test",
                remote="test",
            )
            assert (await service.message_handler(mock_request)).status == 200
        with async_mock.patch.object(
            RedisHTTPHandler,
            "get_direct_responses",
            async_mock.CoroutineMock(side_effect=test_module.asyncio.TimeoutError),
        ), async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            service = RedisHTTPHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            mock_redis.blpop = async_mock.MagicMock()
            mock_redis.rpush = async_mock.MagicMock()
            service.redis = mock_redis
            mock_request = async_mock.MagicMock(
                headers={"content-type": "..."},
                read=async_mock.CoroutineMock(
                    return_value=json.dumps(
                        {
                            "content-type": "application/json",
                            "test": "....",
                            "~transport": {"return_route": "..."},
                        }
                    )
                ),
                host="test",
                remote="test",
            )
            assert (await service.message_handler(mock_request)).status == 200

    async def test_message_handler_x(self):
        with async_mock.patch.object(
            RedisHTTPHandler,
            "get_direct_responses",
            async_mock.CoroutineMock(side_effect=test_module.asyncio.TimeoutError),
        ), async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            service = RedisHTTPHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            mock_redis.blpop = async_mock.MagicMock()
            mock_redis.rpush = async_mock.MagicMock(
                side_effect=[test_module.RedisError, None]
            )
            service.redis = mock_redis
            mock_request = async_mock.MagicMock(
                headers={"content-type": "..."},
                read=async_mock.CoroutineMock(
                    return_value=json.dumps(
                        {"test": "....", "~transport": {"return_route": "..."}}
                    )
                ),
                host="test",
                remote="test",
            )
            await service.message_handler(mock_request)

            service = RedisHTTPHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            mock_redis.blpop = async_mock.MagicMock()
            mock_redis.rpush = async_mock.MagicMock(
                side_effect=[test_module.RedisError, None]
            )
            service.redis = mock_redis
            mock_request = async_mock.MagicMock(
                headers={"content-type": "..."},
                read=async_mock.CoroutineMock(
                    return_value=json.dumps({"test": "...."})
                ),
                host="test",
                remote="test",
            )
            await service.message_handler(mock_request)

    async def test_invite_handler(self):
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            service = RedisHTTPHandler("test", "acapy", "test", "8080")
            service.redis = mock_redis
            await service.invite_handler(async_mock.MagicMock(query={"c_i": ".."}))
            await service.invite_handler(async_mock.MagicMock(query={}))

    def test_is_running(self):
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            sentinel = PropertyMock(return_value=True)
            RedisHTTPHandler.running = sentinel
            service = RedisHTTPHandler("test", "acapy", "test", "8080")
            mock_redis = async_mock.MagicMock(ping=async_mock.MagicMock())
            service.redis = mock_redis
            service.running = True
            assert service.is_running()
            sentinel = PropertyMock(return_value=False)
            RedisHTTPHandler.running = sentinel
            service = RedisHTTPHandler("test", "acapy", "test", "8080")
            mock_redis = async_mock.MagicMock(ping=async_mock.MagicMock())
            service.redis = mock_redis
            service.running = False
            assert not service.is_running()
            sentinel = PropertyMock(return_value=True)
            RedisHTTPHandler.running = sentinel
            service = RedisHTTPHandler("test", "acapy", "test", "8080")
            mock_redis = async_mock.MagicMock(
                ping=async_mock.MagicMock(side_effect=redis.exceptions.RedisError)
            )
            service.redis = mock_redis
            service.running = True
            assert not service.is_running()


class TestRedisWSHandler(AsyncTestCase):
    async def test_main(self):
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis, async_mock.patch.object(
            RedisWSHandler, "start", async_mock.CoroutineMock()
        ), async_mock.patch.object(
            RedisWSHandler, "process_direct_responses", async_mock.CoroutineMock()
        ), async_mock.patch.object(
            Path, "open", async_mock.MagicMock()
        ), async_mock.patch.object(
            uvicorn, "run", async_mock.MagicMock()
        ):
            sentinel = PropertyMock(return_value=False)
            RedisWSHandler.running = sentinel
            main(
                [
                    "-iq",
                    "test",
                    "-iqt",
                    "ws",
                    "0.0.0.0",
                    "8080",
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
                    "-iq",
                    "test",
                ]
            )
        with self.assertRaises(SystemExit):
            main(
                [
                    "-iq",
                    "test",
                    "-iqt",
                    "invalid",
                    "0.0.0.0",
                    "8080",
                    "--endpoint-transport",
                    "0.0.0.0",
                    "8080",
                    "--endpoint-api-key",
                    "test123",
                ]
            )
        with self.assertRaises(SystemExit):
            main(
                [
                    "-iq",
                    "test",
                    "-iqt",
                    "ws",
                    "0.0.0.0",
                    "8080",
                ]
            )
        with self.assertRaises(SystemExit):
            main(
                [
                    "-iq",
                    "test",
                    "-iqt",
                    "ws",
                    "0.0.0.0",
                    "8080",
                    "--endpoint-transport",
                    "0.0.0.0",
                    "8081",
                ]
            )
        sentinel = PropertyMock(return_value=False)
        RedisWSHandler.running = sentinel
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(
                ping=async_mock.MagicMock(side_effect=redis.exceptions.RedisError)
            ),
        ) as mock_redis, async_mock.patch.object(
            RedisWSHandler, "start", async_mock.CoroutineMock()
        ), async_mock.patch.object(
            RedisWSHandler, "process_direct_responses", async_mock.CoroutineMock()
        ), async_mock.patch.object(
            Path, "open", async_mock.MagicMock()
        ), async_mock.patch.object(
            uvicorn, "run", async_mock.MagicMock()
        ):
            main(
                [
                    "-iq",
                    "test",
                    "-iqt",
                    "ws",
                    "0.0.0.0",
                    "8080",
                    "--endpoint-transport",
                    "0.0.0.0",
                    "8080",
                    "--endpoint-api-key",
                    "test123",
                ]
            )

    async def test_stop(self):
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis, async_mock.patch.object(
            test_module.web,
            "TCPSite",
            async_mock.MagicMock(stop=async_mock.CoroutineMock()),
        ) as mock_site:
            mock_redis.blpop = async_mock.MagicMock()
            mock_redis.rpush = async_mock.MagicMock()
            sentinel = PropertyMock(side_effect=[True, True, True, False])
            RedisWSHandler.running = sentinel
            service = RedisWSHandler("test", "acapy", "test", "8080")
            service.site = async_mock.MagicMock(stop=async_mock.CoroutineMock())
            service.redis = mock_redis
            await service.stop()

    async def test_start(self):
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis, async_mock.patch.object(
            test_module.web,
            "TCPSite",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    stop=async_mock.CoroutineMock(),
                    start=async_mock.CoroutineMock(),
                )
            ),
        ), async_mock.patch.object(
            test_module.web.AppRunner,
            "setup",
            async_mock.CoroutineMock(),
        ):
            sentinel = PropertyMock(side_effect=[True, True, True, False])
            RedisWSHandler.running = sentinel
            service = RedisWSHandler("test", "acapy", "test", "8080")
            mock_redis.blpop = async_mock.MagicMock()
            mock_redis.rpush = async_mock.MagicMock()
            service.redis = mock_redis
            await service.start()

    async def test_process_direct_response(self):
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            mock_redis.blpop = async_mock.MagicMock(
                side_effect=[
                    (None, test_retry_msg_a),
                    (None, test_retry_msg_b),
                    (None, test_retry_msg_c),
                    test_module.RedisError,
                    (None, test_retry_msg_d),
                ]
            )
            sentinel = PropertyMock(side_effect=[True, True, True, True, False])
            RedisWSHandler.running = sentinel
            service = RedisWSHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            service.redis = mock_redis
            assert service.direct_response_txn_request_map == {}
            await service.process_direct_responses()
            assert service.direct_response_txn_request_map != {}

    async def test_get_direct_response(self):
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            sentinel = PropertyMock(side_effect=[True, True, False])
            RedisWSHandler.running = sentinel
            service = RedisWSHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            service.redis = mock_redis
            service.direct_response_txn_request_map = {
                "txn_123": b"test",
                "txn_124": b"test2",
            }
            await service.get_direct_responses("txn_321")
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            sentinel = PropertyMock(side_effect=[True, False])
            RedisWSHandler.running = sentinel
            service = RedisWSHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            service.redis = mock_redis
            service.direct_response_txn_request_map = {
                "txn_123": b"test",
                "txn_124": b"test2",
            }
            await service.get_direct_responses("txn_123") == b"test"
            await service.get_direct_responses("txn_124") == b"test2"

    async def test_message_handler_a(self):
        mock_request = async_mock.MagicMock(
            host="test",
            remote="test",
        )
        mock_msg = async_mock.MagicMock(
            type=aiohttp.WSMsgType.TEXT.value,
            data=json.dumps({"test": "....", "~transport": {"return_route": "..."}}),
        )

        with async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "prepare",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "receive",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "closed",
            PropertyMock(side_effect=[False, False, True, False]),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "close",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "exception",
            async_mock.MagicMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "send_bytes",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "send_str",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.asyncio,
            "get_event_loop",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    run_until_complete=async_mock.MagicMock(),
                    create_task=async_mock.MagicMock(
                        return_value=async_mock.MagicMock(
                            done=async_mock.MagicMock(return_value=True),
                            result=async_mock.MagicMock(return_value=mock_msg),
                        )
                    ),
                )
            ),
        ) as mock_get_event_loop, async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait, async_mock.patch.object(
            RedisWSHandler,
            "get_direct_responses",
            autospec=True,
        ) as mock_get_direct_responses, async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            mock_get_direct_responses.return_value = {"response": b"..."}
            service = RedisWSHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            mock_redis.blpop = async_mock.MagicMock()
            mock_redis.rpush = async_mock.MagicMock()
            service.redis = mock_redis
            await service.message_handler(mock_request)

    async def test_message_handler_b(self):
        mock_request = async_mock.MagicMock(
            host="test",
            remote="test",
        )
        mock_msg = async_mock.MagicMock(
            type=aiohttp.WSMsgType.TEXT.value,
            data=json.dumps({"test": "....", "~transport": {"return_route": "..."}}),
        )

        with async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "prepare",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "receive",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "closed",
            PropertyMock(side_effect=[False, False, True, False]),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "close",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "exception",
            async_mock.MagicMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "send_bytes",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "send_str",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.asyncio,
            "get_event_loop",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    run_until_complete=async_mock.MagicMock(),
                    create_task=async_mock.MagicMock(
                        return_value=async_mock.MagicMock(
                            done=async_mock.MagicMock(return_value=True),
                            result=async_mock.MagicMock(return_value=mock_msg),
                        )
                    ),
                )
            ),
        ) as mock_get_event_loop, async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait, async_mock.patch.object(
            RedisWSHandler,
            "get_direct_responses",
            autospec=True,
        ) as mock_get_direct_responses, async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            mock_get_direct_responses.return_value = {"response": "..."}
            service = RedisWSHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            mock_redis.blpop = async_mock.MagicMock()
            mock_redis.rpush = async_mock.MagicMock()
            service.redis = mock_redis
            await service.message_handler(mock_request)

    async def test_message_handler_c(self):
        mock_request = async_mock.MagicMock(
            host="test",
            remote="test",
        )
        mock_msg = async_mock.MagicMock(
            type=aiohttp.WSMsgType.TEXT.value,
            data=json.dumps({"test": "...."}),
        )

        with async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "prepare",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "receive",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "closed",
            PropertyMock(side_effect=[False, False, True, False]),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "close",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "exception",
            async_mock.MagicMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "send_bytes",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "send_str",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.asyncio,
            "get_event_loop",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    run_until_complete=async_mock.MagicMock(),
                    create_task=async_mock.MagicMock(
                        return_value=async_mock.MagicMock(
                            done=async_mock.MagicMock(return_value=True),
                            result=async_mock.MagicMock(return_value=mock_msg),
                        )
                    ),
                )
            ),
        ) as mock_get_event_loop, async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait, async_mock.patch.object(
            RedisWSHandler,
            "get_direct_responses",
            autospec=True,
        ) as mock_get_direct_responses, async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            service = RedisWSHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            mock_redis.blpop = async_mock.MagicMock()
            mock_redis.rpush = async_mock.MagicMock()
            service.redis = mock_redis
            await service.message_handler(mock_request)

    async def test_message_handler_x(self):
        mock_request = async_mock.MagicMock(
            host="test",
            remote="test",
        )
        mock_msg = async_mock.MagicMock(
            type=aiohttp.WSMsgType.TEXT.value,
            data=json.dumps({"test": "....", "~transport": {"return_route": "..."}}),
        )

        with async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "prepare",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "receive",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "closed",
            PropertyMock(side_effect=[False, False, True, False]),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "close",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "exception",
            async_mock.MagicMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "send_bytes",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "send_str",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.asyncio,
            "get_event_loop",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    run_until_complete=async_mock.MagicMock(),
                    create_task=async_mock.MagicMock(
                        return_value=async_mock.MagicMock(
                            done=async_mock.MagicMock(return_value=True),
                            result=async_mock.MagicMock(return_value=mock_msg),
                        )
                    ),
                )
            ),
        ) as mock_get_event_loop, async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait, async_mock.patch.object(
            RedisWSHandler,
            "get_direct_responses",
            autospec=True,
        ) as mock_get_direct_responses, async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            mock_get_direct_responses.side_effect = test_module.asyncio.TimeoutError
            service = RedisWSHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            mock_redis.blpop = async_mock.MagicMock()
            mock_redis.rpush = async_mock.MagicMock()
            service.redis = mock_redis
            await service.message_handler(mock_request)

        mock_msg = async_mock.MagicMock(
            type=aiohttp.WSMsgType.TEXT.value,
            data=json.dumps({"test": "....", "~transport": {"return_route": "..."}}),
        )

        with async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "prepare",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "receive",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "closed",
            PropertyMock(side_effect=[False, False, True, False]),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "close",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "exception",
            async_mock.MagicMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "send_bytes",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "send_str",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.asyncio,
            "get_event_loop",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    run_until_complete=async_mock.MagicMock(),
                    create_task=async_mock.MagicMock(
                        return_value=async_mock.MagicMock(
                            done=async_mock.MagicMock(return_value=True),
                            result=async_mock.MagicMock(return_value=mock_msg),
                        )
                    ),
                )
            ),
        ) as mock_get_event_loop, async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait, async_mock.patch.object(
            RedisWSHandler,
            "get_direct_responses",
            autospec=True,
        ) as mock_get_direct_responses, async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            service = RedisWSHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            mock_redis.blpop = async_mock.MagicMock()
            mock_redis.rpush = async_mock.MagicMock(
                side_effect=[test_module.RedisError, None]
            )
            service.redis = mock_redis
            await service.message_handler(mock_request)

        mock_msg = async_mock.MagicMock(
            type=aiohttp.WSMsgType.ERROR.value,
            data=json.dumps({"test": "...."}),
        )

        with async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "prepare",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "receive",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "closed",
            PropertyMock(side_effect=[False, False, True, True]),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "close",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "exception",
            async_mock.MagicMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "send_bytes",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "send_str",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.asyncio,
            "get_event_loop",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    run_until_complete=async_mock.MagicMock(),
                    create_task=async_mock.MagicMock(
                        return_value=async_mock.MagicMock(
                            done=async_mock.MagicMock(return_value=True),
                            result=async_mock.MagicMock(return_value=mock_msg),
                        )
                    ),
                )
            ),
        ) as mock_get_event_loop, async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait, async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            service = RedisWSHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            mock_redis.blpop = async_mock.MagicMock()
            mock_redis.rpush = async_mock.MagicMock()
            service.redis = mock_redis
            await service.message_handler(mock_request)

        mock_msg = async_mock.MagicMock(
            type="invlaid",
            data=json.dumps({"test": "...."}),
        )

        with async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "prepare",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "receive",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "closed",
            PropertyMock(side_effect=[False, False, True, True]),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "close",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "exception",
            async_mock.MagicMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "send_bytes",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "send_str",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.asyncio,
            "get_event_loop",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    run_until_complete=async_mock.MagicMock(),
                    create_task=async_mock.MagicMock(
                        return_value=async_mock.MagicMock(
                            done=async_mock.MagicMock(return_value=True),
                            result=async_mock.MagicMock(return_value=mock_msg),
                        )
                    ),
                )
            ),
        ) as mock_get_event_loop, async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait, async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            service = RedisWSHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            mock_redis.blpop = async_mock.MagicMock()
            mock_redis.rpush = async_mock.MagicMock()
            service.redis = mock_redis
            await service.message_handler(mock_request)

        mock_msg = async_mock.MagicMock(
            type=aiohttp.WSMsgType.TEXT.value,
            data=json.dumps({"test": "...."}),
        )

        with async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "prepare",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "receive",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "closed",
            PropertyMock(side_effect=[False, False, True, False]),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "close",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "exception",
            async_mock.MagicMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "send_bytes",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.web.WebSocketResponse,
            "send_str",
            async_mock.CoroutineMock(),
        ), async_mock.patch.object(
            test_module.asyncio,
            "get_event_loop",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    run_until_complete=async_mock.MagicMock(),
                    create_task=async_mock.MagicMock(
                        return_value=async_mock.MagicMock(
                            done=async_mock.MagicMock(return_value=True),
                            result=async_mock.MagicMock(return_value=mock_msg),
                        )
                    ),
                )
            ),
        ) as mock_get_event_loop, async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait, async_mock.patch.object(
            test_module.asyncio,
            "wait_for",
            async_mock.CoroutineMock(),
        ) as mock_wait_for, async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            service = RedisWSHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            mock_redis.blpop = async_mock.MagicMock()
            mock_redis.rpush = async_mock.MagicMock(
                side_effect=[test_module.RedisError, None]
            )
            service.redis = mock_redis
            await service.message_handler(mock_request)

    def test_status_live(self):
        test_module.API_KEY = "test1234"
        test_module.handlers = [
            async_mock.MagicMock(is_running=async_mock.MagicMock(return_value=False)),
            async_mock.MagicMock(is_running=async_mock.MagicMock(return_value=True)),
        ]
        assert test_module.status_live(api_key="test1234") == {"alive": False}
        test_module.handlers = [
            async_mock.MagicMock(is_running=async_mock.MagicMock(return_value=True)),
            async_mock.MagicMock(is_running=async_mock.MagicMock(return_value=True)),
        ]
        assert test_module.status_live(api_key="test1234") == {"alive": True}

    def test_status_ready(self):
        test_module.API_KEY = "test1234"
        test_module.handlers = [
            async_mock.MagicMock(ready=False),
            async_mock.MagicMock(ready=True),
        ]
        assert test_module.status_ready(api_key="test1234") == {"ready": False}
        test_module.handlers = [
            async_mock.MagicMock(ready=True),
            async_mock.MagicMock(ready=True),
        ]
        assert test_module.status_ready(api_key="test1234") == {"ready": True}

    def test_is_running(self):
        with async_mock.patch.object(
            redis.cluster.RedisCluster,
            "from_url",
            async_mock.MagicMock(),
        ) as mock_redis:
            sentinel = PropertyMock(return_value=True)
            RedisWSHandler.running = sentinel
            service = RedisWSHandler("test", "acapy", "test", "8080")
            mock_redis = async_mock.MagicMock(ping=async_mock.MagicMock())
            service.redis = mock_redis
            service.running = True
            assert service.is_running()
            sentinel = PropertyMock(return_value=False)
            RedisWSHandler.running = sentinel
            service = RedisWSHandler("test", "acapy", "test", "8080")
            mock_redis = async_mock.MagicMock(ping=async_mock.MagicMock())
            service.redis = mock_redis
            service.running = False
            assert not service.is_running()
            sentinel = PropertyMock(return_value=True)
            RedisWSHandler.running = sentinel
            service = RedisWSHandler("test", "acapy", "test", "8080")
            mock_redis = async_mock.MagicMock(
                ping=async_mock.MagicMock(side_effect=redis.exceptions.RedisError)
            )
            service.redis = mock_redis
            service.running = True
            assert not service.is_running()
