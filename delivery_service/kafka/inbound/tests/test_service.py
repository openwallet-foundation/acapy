import aiohttp
import msgpack
import json
import uvicorn

from aiokafka import TopicPartition, ConsumerRecord
from asynctest import TestCase as AsyncTestCase, mock as async_mock, PropertyMock
from pathlib import Path
from time import time

from .. import service as test_module
from ..service import KafkaHTTPHandler, KafkaWSHandler, main

test_retry_msg_sets = {
    TopicPartition("acapy.inbound_direct_responses", 0): [
        ConsumerRecord(
            value=msgpack.packb(["invalid", "list", "require", "dict"]),
            key="test_random_1",
            offset=1001,
            partition=0,
            topic="acapy.inbound_direct_responses",
            timestamp=int(time()),
            timestamp_type=1,
            checksum=123232,
            serialized_key_size=123,
            serialized_value_size=12321,
            headers=[("test", b"test")],
        ),
        ConsumerRecord(
            value=msgpack.packb(
                {
                    "response_data": (bytes(range(0, 256))),
                }
            ),
            key="test_random_1",
            offset=1001,
            partition=0,
            topic="acapy.inbound_direct_responses",
            timestamp=int(time()),
            timestamp_type=1,
            checksum=123232,
            serialized_key_size=123,
            serialized_value_size=12321,
            headers=[("test", b"test")],
        ),
        ConsumerRecord(
            value=msgpack.packb(
                {
                    "response_data": (bytes(range(0, 256))),
                }
            ),
            key="test_random_1",
            offset=1001,
            partition=0,
            topic="acapy.inbound_direct_responses",
            timestamp=int(time()),
            timestamp_type=1,
            checksum=123232,
            serialized_key_size=123,
            serialized_value_size=12321,
            headers=[("test", b"test")],
        ),
        ConsumerRecord(
            value=msgpack.packb(
                {
                    "response_data": (bytes(range(0, 256))),
                    "txn_id": "test123",
                }
            ),
            key="test_random_1",
            offset=1001,
            partition=0,
            topic="acapy.inbound_direct_responses",
            timestamp=int(time()),
            timestamp_type=1,
            checksum=123232,
            serialized_key_size=123,
            serialized_value_size=12321,
            headers=[("test", b"test")],
        ),
        ConsumerRecord(
            value=msgpack.packb(
                {
                    "txn_id": "test123",
                }
            ),
            key="test_random_1",
            offset=1001,
            partition=0,
            topic="acapy.inbound_direct_responses",
            timestamp=int(time()),
            timestamp_type=1,
            checksum=123232,
            serialized_key_size=123,
            serialized_value_size=12321,
            headers=[("test", b"test")],
        ),
    ]
}


class TestKafkaHTTPHandler(AsyncTestCase):
    async def test_main(self):
        with async_mock.patch(
            "aiokafka.AIOKafkaProducer.start",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaProducer",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.start",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer",
            async_mock.MagicMock(),
        ), async_mock.patch.object(
            KafkaHTTPHandler, "start", autospec=True
        ), async_mock.patch.object(
            KafkaHTTPHandler, "process_direct_responses", autospec=True
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

    async def test_stop(self):
        sentinel = PropertyMock(side_effect=[True, True, True, False])
        KafkaHTTPHandler.running = sentinel
        service = KafkaHTTPHandler("test", "acapy", "test", "8080")
        with async_mock.patch.object(
            test_module.web,
            "TCPSite",
            async_mock.MagicMock(stop=async_mock.CoroutineMock()),
        ) as mock_site:
            mock_producer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                transaction=async_mock.MagicMock(),
                send=async_mock.CoroutineMock(),
            )
            mock_consumer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
            )
            service.producer = mock_producer
            service.consumer_direct_response = mock_consumer
            service.site = async_mock.MagicMock(stop=async_mock.CoroutineMock())
            await service.stop()

    async def test_start(self):
        sentinel = PropertyMock(side_effect=[True, True, True, False])
        KafkaHTTPHandler.running = sentinel
        service = KafkaHTTPHandler("test", "acapy", "test", "8080")
        with async_mock.patch.object(
            test_module.web,
            "TCPSite",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    start=async_mock.CoroutineMock(),
                    stop=async_mock.CoroutineMock(),
                )
            ),
        ), async_mock.patch.object(
            test_module.web.AppRunner,
            "setup",
            async_mock.CoroutineMock(),
        ):
            mock_producer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                transaction=async_mock.MagicMock(),
                send=async_mock.CoroutineMock(),
            )
            service.producer = mock_producer
            await service.start()

    async def test_process_direct_response(self):
        sentinel = PropertyMock(side_effect=[True, False])
        KafkaHTTPHandler.running = sentinel
        service = KafkaHTTPHandler("test", "acapy", "test", "8080")
        mock_consumer = async_mock.MagicMock(
            start=async_mock.CoroutineMock(),
            stop=async_mock.CoroutineMock(),
            subscribe=async_mock.CoroutineMock(),
            getmany=async_mock.CoroutineMock(
                side_effect=[
                    test_retry_msg_sets,
                ]
            ),
            seek_to_beginning=async_mock.CoroutineMock(),
        )
        service.consumer_direct_response = mock_consumer
        service.timedelay_s = 0.1
        assert service.direct_response_txn_request_map == {}
        await service.process_direct_responses()
        assert service.direct_response_txn_request_map != {}

    async def test_get_direct_response(self):
        sentinel = PropertyMock(side_effect=[True, True, False])
        KafkaHTTPHandler.running = sentinel
        service = KafkaHTTPHandler("test", "acapy", "test", "8080")
        service.timedelay_s = 0.1
        service.direct_response_txn_request_map = {
            "txn_123": b"test",
            "txn_124": b"test2",
        }
        await service.get_direct_responses("txn_321")
        sentinel = PropertyMock(side_effect=[True, True, False])
        KafkaHTTPHandler.running = sentinel
        service = KafkaHTTPHandler("test", "acapy", "test", "8080")
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
        mock_producer = async_mock.MagicMock(
            start=async_mock.CoroutineMock(),
            stop=async_mock.CoroutineMock(),
            transaction=async_mock.MagicMock(),
            send=async_mock.CoroutineMock(),
        )
        sentinel = PropertyMock(side_effect=[True, False])
        KafkaHTTPHandler.running = sentinel
        service = KafkaHTTPHandler("test", "acapy", "test", "8080")
        service.timedelay_s = 0.1
        service.producer = mock_producer
        assert (await service.message_handler(mock_request)).status == 200
        with async_mock.patch.object(
            KafkaHTTPHandler,
            "get_direct_responses",
            async_mock.CoroutineMock(
                return_value={"response": json.dumps({"test": "...."})}
            ),
        ):
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
            service = KafkaHTTPHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            service.producer = mock_producer
            assert (await service.message_handler(mock_request)).status == 200
        with async_mock.patch.object(
            KafkaHTTPHandler,
            "get_direct_responses",
            async_mock.CoroutineMock(side_effect=test_module.asyncio.TimeoutError),
        ):
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
            service = KafkaHTTPHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            service.producer = mock_producer
            assert (await service.message_handler(mock_request)).status == 200

    async def test_invite_handler(self):
        service = KafkaHTTPHandler("test", "acapy", "test", "8080")
        await service.invite_handler(async_mock.MagicMock(query={"c_i": ".."}))
        await service.invite_handler(async_mock.MagicMock(query={}))

    def test_parse_connection_url(self):
        service = KafkaHTTPHandler(
            "localhost:8080,localhost:8081#username:password", "acapy", "test", "8080"
        )
        assert service._host == "localhost:8080,localhost:8081"
        assert service.username == "username"
        assert service.password == "password"


class TestKafkaWSHandler(AsyncTestCase):
    async def test_main(self):
        with async_mock.patch.object(
            KafkaWSHandler, "start", autospec=True
        ), async_mock.patch.object(
            KafkaWSHandler, "process_direct_responses", autospec=True
        ), async_mock.patch(
            "aiokafka.AIOKafkaProducer.start",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaProducer",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.start",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer",
            async_mock.MagicMock(),
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
                    "8080",
                ]
            )

    async def test_stop(self):
        sentinel = PropertyMock(side_effect=[True, True, True, False])
        KafkaWSHandler.running = sentinel
        service = KafkaWSHandler("test", "acapy", "test", "8080")
        with async_mock.patch.object(
            test_module.web,
            "TCPSite",
            async_mock.MagicMock(stop=async_mock.CoroutineMock()),
        ) as mock_site:
            mock_producer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                transaction=async_mock.MagicMock(),
                send=async_mock.CoroutineMock(),
            )
            mock_consumer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
            )
            service.producer = mock_producer
            service.consumer_direct_response = mock_consumer
            service.site = async_mock.MagicMock(stop=async_mock.CoroutineMock())
            await service.stop()

    async def test_start(self):
        sentinel = PropertyMock(side_effect=[True, True, True, False])
        KafkaWSHandler.running = sentinel
        service = KafkaWSHandler("test", "acapy", "test", "8080")
        with async_mock.patch.object(
            test_module.web,
            "TCPSite",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    start=async_mock.CoroutineMock(),
                    stop=async_mock.CoroutineMock(),
                )
            ),
        ), async_mock.patch.object(
            test_module.web.AppRunner,
            "setup",
            async_mock.CoroutineMock(),
        ):
            mock_producer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                transaction=async_mock.MagicMock(),
                send=async_mock.CoroutineMock(),
            )
            service.producer = mock_producer
            await service.start()

    async def test_process_direct_response(self):
        sentinel = PropertyMock(side_effect=[True, False])
        KafkaWSHandler.running = sentinel
        service = KafkaWSHandler("test", "acapy", "test", "8080")
        mock_consumer = async_mock.MagicMock(
            start=async_mock.CoroutineMock(),
            stop=async_mock.CoroutineMock(),
            subscribe=async_mock.CoroutineMock(),
            getmany=async_mock.CoroutineMock(
                side_effect=[
                    test_retry_msg_sets,
                ]
            ),
            seek_to_beginning=async_mock.CoroutineMock(),
        )
        service.consumer_direct_response = mock_consumer
        service.timedelay_s = 0.1
        assert service.direct_response_txn_request_map == {}
        await service.process_direct_responses()
        assert service.direct_response_txn_request_map != {}

    async def test_get_direct_response(self):
        sentinel = PropertyMock(side_effect=[True, True, False])
        KafkaWSHandler.running = sentinel
        service = KafkaWSHandler("test", "acapy", "test", "8080")
        service.timedelay_s = 0.1
        service.direct_response_txn_request_map = {
            "txn_123": b"test",
            "txn_124": b"test2",
        }
        await service.get_direct_responses("txn_321")
        sentinel = PropertyMock(side_effect=[True, False])
        KafkaWSHandler.running = sentinel
        service = KafkaWSHandler("test", "acapy", "test", "8080")
        service.timedelay_s = 0.1
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
            KafkaWSHandler,
            "get_direct_responses",
            autospec=True,
        ) as mock_get_direct_responses:
            mock_get_direct_responses.return_value = {"response": b"..."}
            mock_producer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                transaction=async_mock.MagicMock(),
                send=async_mock.CoroutineMock(),
            )
            service = KafkaWSHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            service.producer = mock_producer
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
            KafkaWSHandler,
            "get_direct_responses",
            autospec=True,
        ) as mock_get_direct_responses:
            mock_get_direct_responses.return_value = {"response": "..."}
            mock_producer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                transaction=async_mock.MagicMock(),
                send=async_mock.CoroutineMock(),
            )
            service = KafkaWSHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            service.producer = mock_producer
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
            KafkaWSHandler,
            "get_direct_responses",
            autospec=True,
        ) as mock_get_direct_responses:
            mock_producer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                transaction=async_mock.MagicMock(),
                send=async_mock.CoroutineMock(),
            )
            service = KafkaWSHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            service.producer = mock_producer
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
            KafkaWSHandler,
            "get_direct_responses",
            autospec=True,
        ) as mock_get_direct_responses:
            mock_get_direct_responses.side_effect = test_module.asyncio.TimeoutError
            mock_producer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                transaction=async_mock.MagicMock(),
                send=async_mock.CoroutineMock(),
            )
            service = KafkaWSHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            service.producer = mock_producer
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
        ) as mock_wait:
            mock_producer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                transaction=async_mock.MagicMock(),
                send=async_mock.CoroutineMock(),
            )
            service = KafkaWSHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            service.producer = mock_producer
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
        ) as mock_wait:
            mock_producer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                transaction=async_mock.MagicMock(),
                send=async_mock.CoroutineMock(),
            )
            service = KafkaWSHandler("test", "acapy", "test", "8080")
            service.timedelay_s = 0.1
            service.producer = mock_producer
            await service.message_handler(mock_request)

    def test_parse_connection_url(self):
        service = KafkaWSHandler(
            "localhost:8080,localhost:8081#username:password", "acapy", "test", "8080"
        )
        assert service._host == "localhost:8080,localhost:8081"
        assert service.username == "username"
        assert service.password == "password"

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
