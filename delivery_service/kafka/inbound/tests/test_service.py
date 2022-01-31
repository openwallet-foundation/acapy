from more_itertools import side_effect
import msgpack
import string
import json

from asynctest import TestCase as AsyncTestCase, mock as async_mock, PropertyMock
from pathlib import Path
from time import time

from .. import service as test_module
from ..service import KafkaHTTPHandler, KafkaWSHandler, main

test_msg_sets_a = {
    "acapy.outbound_transport": [
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    "headers": {"content-type": "test"},
                    "endpoint": "http://localhost:9000",
                    "payload": (string.digits + string.ascii_letters).encode(
                        encoding="utf-8"
                    ),
                }
            ),
            key="test_random_2",
            offsets=1003,
        ),
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    "headers": {"content-type": b"test1"},
                    "endpoint": "http://localhost:9000",
                    "payload": (string.digits + string.ascii_letters).encode(
                        encoding="utf-8"
                    ),
                }
            ),
            key="test_random_3",
            offsets=1002,
        ),
    ]
}
test_msg_sets_b = {
    "acapy.outbound_transport": [
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    "headers": {"content-type": "test1"},
                    "endpoint": "http://localhost:9000",
                    "payload": (bytes(range(0, 256))),
                }
            ),
            key="test_random_1",
            offsets=1001,
        )
    ]
}
test_msg_sets_c = {
    "acapy.outbound_transport": [
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    "headers": {"content-type": "test1"},
                    "endpoint": "http://localhost:9000",
                    "payload": (bytes(range(0, 256))),
                    "retries": 6,
                }
            ),
            key="test_random_1",
            offsets=1001,
        )
    ]
}
test_retry_msg_sets = {
    "acapy.inbound_direct_responses": [
        async_mock.MagicMock(
            value=msgpack.packb(["invalid", "list", "require", "dict"]),
            key="test_random_1",
            offsets=1001,
        ),
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    "response_data": (bytes(range(0, 256))),
                }
            ),
            key="test_random_1",
            offsets=1001,
        ),
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    "response_data": (bytes(range(0, 256))),
                    "txn_id": "test123",
                }
            ),
            key="test_random_1",
            offsets=1001,
        ),
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    "txn_id": "test123",
                }
            ),
            key="test_random_1",
            offsets=1001,
        ),
    ]
}
test_msg_sets_d = {
    "acapy.outbound_transport": [
        async_mock.MagicMock(
            value=msgpack.packb(["invalid", "list", "require", "dict"]),
            key="test_random_1",
            offsets=1001,
        ),
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    "headers": {"content-type": "test1"},
                    "payload": (bytes(range(0, 256))),
                }
            ),
            key="test_random_1",
            offsets=1001,
        ),
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    "headers": {"content-type": "test1"},
                    "endpoint": "http://localhost:9000",
                    "payload": (bytes(range(0, 256))),
                    "retries": 6,
                }
            ),
            key="test_random_1",
            offsets=1001,
        ),
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    "headers": {"content-type": "test1"},
                    "endpoint": "ws://localhost:9000",
                    "payload": (bytes(range(0, 256))),
                }
            ),
            key="test_random_1",
            offsets=1001,
        ),
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    "headers": {"content-type": "test1"},
                    "endpoint": "http://localhost:9000",
                }
            ),
            key="test_random_1",
            offsets=1001,
        ),
    ]
}
test_msg_sets_e = {
    "acapy.outbound_retry": [
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    "headers": {"content-type": "test1"},
                    "endpoint": "http://localhost:9000",
                    "payload": (bytes(range(0, 256))),
                    "retry_time": int(time()),
                }
            ),
            key="test_random_1",
            offsets=1001,
        )
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
        ):
            await main(
                [
                    "-iq",
                    "test",
                    "-it",
                    "http",
                    "0.0.0.0",
                    "8080",
                ]
            )

    async def test_main_x(self):
        with self.assertRaises(SystemExit):
            await main([])
        with self.assertRaises(SystemExit):
            await main(
                [
                    "-iq",
                    "test",
                ]
            )
        with self.assertRaises(SystemExit):
            await main(
                [
                    "-iq",
                    "test",
                    "-it",
                    "invalid",
                    "0.0.0.0",
                    "8080",
                ]
            )

    async def test_main_plugin_config(self):
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
            test_module.yaml,
            "safe_load",
            async_mock.MagicMock(
                return_value={"kafka_inbound_queue": {"connection": "test"}}
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
                    "-it",
                    "http",
                    "0.0.0.0",
                    "8080",
                ]
            )

    async def test_stop(self):
        sentinel = PropertyMock(side_effect=[True, True, True, False])
        KafkaHTTPHandler.RUNNING = sentinel
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
            await service.stop()

    async def test_start(self):
        sentinel = PropertyMock(side_effect=[True, True, True, False])
        KafkaHTTPHandler.RUNNING = sentinel
        service = KafkaHTTPHandler("test", "acapy", "test", "8080")
        with async_mock.patch.object(
            test_module.web,
            "TCPSite",
            async_mock.MagicMock(stop=async_mock.CoroutineMock()),
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
        KafkaHTTPHandler.RUNNING_DIRECT_RESP = sentinel
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
        sentinel = PropertyMock(side_effect=[True, False])
        KafkaHTTPHandler.RUNNING = sentinel
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
        KafkaHTTPHandler.RUNNING = sentinel
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
        await service.invite_handler(
            async_mock.MagicMock(query=async_mock.MagicMock(return_value={"c_i": ".."}))
        )
        await service.invite_handler(
            async_mock.MagicMock(query=async_mock.MagicMock(return_value={}))
        )


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
        ):
            await main(
                [
                    "-iq",
                    "test",
                    "-it",
                    "ws",
                    "0.0.0.0",
                    "8080",
                ]
            )

    async def test_main_x(self):
        with self.assertRaises(SystemExit):
            await main([])
        with self.assertRaises(SystemExit):
            await main(
                [
                    "-iq",
                    "test",
                ]
            )
        with self.assertRaises(SystemExit):
            await main(
                [
                    "-iq",
                    "test",
                    "-it",
                    "invalid",
                    "0.0.0.0",
                    "8080",
                ]
            )

    async def test_main_plugin_config(self):
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
            test_module.yaml,
            "safe_load",
            async_mock.MagicMock(
                return_value={"kafka_inbound_queue": {"connection": "test"}}
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
                    "-it",
                    "ws",
                    "0.0.0.0",
                    "8080",
                ]
            )

    async def test_stop(self):
        sentinel = PropertyMock(side_effect=[True, True, True, False])
        KafkaWSHandler.RUNNING = sentinel
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
            await service.stop()

    async def test_start(self):
        sentinel = PropertyMock(side_effect=[True, True, True, False])
        KafkaWSHandler.RUNNING = sentinel
        service = KafkaWSHandler("test", "acapy", "test", "8080")
        with async_mock.patch.object(
            test_module.web,
            "TCPSite",
            async_mock.MagicMock(stop=async_mock.CoroutineMock()),
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
        KafkaHTTPHandler.RUNNING_DIRECT_RESP = sentinel
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
        sentinel = PropertyMock(side_effect=[True, False])
        KafkaHTTPHandler.RUNNING = sentinel
        service = KafkaHTTPHandler("test", "acapy", "test", "8080")
        service.timedelay_s = 0.1
        service.direct_response_txn_request_map = {
            "txn_123": b"test",
            "txn_124": b"test2",
        }
        await service.get_direct_responses("txn_123") == b"test"
        await service.get_direct_responses("txn_124") == b"test2"

    async def test_message_handler(self):
        pass

    async def test_invite_handler(self):
        pass
