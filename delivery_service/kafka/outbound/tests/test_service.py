import msgpack
import os
import string
import uvicorn

import aiohttp
import asyncio

from aiokafka import TopicPartition, ConsumerRecord
from aiokafka.errors import OffsetOutOfRangeError
from asynctest import TestCase as AsyncTestCase, mock as async_mock, PropertyMock
from pathlib import Path
from time import time

from .. import service as test_module
from ..service import KafkaHandler, RebalanceListener, main, argument_parser

test_msg_sets_a = {
    TopicPartition("acapy.outbound_transport", 0): [
        ConsumerRecord(
            value=msgpack.packb(
                {
                    b"headers": {b"content-type": b"test"},
                    b"endpoint": b"http://localhost:9000",
                    b"payload": (string.digits + string.ascii_letters).encode("utf-8"),
                }
            ),
            key="test_random_2",
            offset=1003,
            partition=0,
            topic="acapy.outbound_transport",
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
                    b"headers": {b"content-type": b"test1"},
                    b"endpoint": b"http://localhost:9000",
                    b"payload": (string.digits + string.ascii_letters).encode("utf-8"),
                }
            ),
            key="test_random_3",
            offset=1002,
            partition=0,
            topic="acapy.outbound_transport",
            timestamp=int(time()),
            timestamp_type=1,
            checksum=123232,
            serialized_key_size=123,
            serialized_value_size=12321,
            headers=[("test", b"test")],
        ),
    ]
}
test_msg_sets_b = {
    TopicPartition("acapy.outbound_transport", 0): [
        ConsumerRecord(
            value=msgpack.packb(
                {
                    b"headers": {b"content-type": b"test1"},
                    b"endpoint": b"http://localhost:9000",
                    b"payload": (string.digits + string.ascii_letters).encode("utf-8"),
                }
            ),
            key="test_random_1",
            offset=1001,
            partition=0,
            topic="acapy.outbound_transport",
            timestamp=int(time()),
            timestamp_type=1,
            checksum=123232,
            serialized_key_size=123,
            serialized_value_size=12321,
            headers=[("test", b"test")],
        ),
    ]
}
test_msg_sets_c = {
    TopicPartition("acapy.outbound_transport", 0): [
        ConsumerRecord(
            value=msgpack.packb(
                {
                    b"headers": {b"content-type": b"test1"},
                    b"endpoint": b"http://localhost:9000",
                    b"payload": (string.digits + string.ascii_letters).encode("utf-8"),
                    b"retries": 6,
                }
            ),
            key="test_random_1",
            offset=1001,
            partition=0,
            topic="acapy.outbound_transport",
            timestamp=int(time()),
            timestamp_type=1,
            checksum=123232,
            serialized_key_size=123,
            serialized_value_size=12321,
            headers=[("test", b"test")],
        ),
    ]
}
test_msg_sets_d = {
    TopicPartition("acapy.outbound_transport", 0): [
        ConsumerRecord(
            value=msgpack.packb(["invalid", "list", "require", "dict"]),
            key="test_random_1",
            offset=1001,
            partition=0,
            topic="acapy.outbound_transport",
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
                    b"headers": {b"content-type": b"test1"},
                    "payload": (string.digits + string.ascii_letters).encode("utf-8"),
                }
            ),
            key="test_random_1",
            offset=1001,
            partition=0,
            topic="acapy.outbound_transport",
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
                    "headers": {b"content-type": b"test1"},
                    b"endpoint": b"http://localhost:9000",
                    b"payload": (string.digits + string.ascii_letters).encode("utf-8"),
                    b"retries": 6,
                }
            ),
            key="test_random_1",
            offset=1001,
            partition=0,
            topic="acapy.outbound_transport",
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
                    b"headers": {b"content-type": b"test1"},
                    "endpoint": b"ws://localhost:9000",
                    b"payload": (string.digits + string.ascii_letters).encode("utf-8"),
                }
            ),
            key="test_random_1",
            offset=1001,
            partition=0,
            topic="acapy.outbound_transport",
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
                    b"headers": {b"content-type": b"test1"},
                    b"endpoint": b"ws://localhost:9000",
                    b"payload": (string.digits + string.ascii_letters).encode("utf-8"),
                }
            ),
            key="test_random_1",
            offset=1001,
            partition=0,
            topic="acapy.outbound_transport",
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
                    b"headers": {b"content-type": "test1"},
                    b"endpoint": b"ws://localhost:9000",
                }
            ),
            key="test_random_1",
            offset=1001,
            partition=0,
            topic="acapy.outbound_transport",
            timestamp=int(time()),
            timestamp_type=1,
            checksum=123232,
            serialized_key_size=123,
            serialized_value_size=12321,
            headers=[("test", b"test")],
        ),
    ]
}
test_msg_sets_e = {
    TopicPartition("acapy.outbound_transport", 0): [
        ConsumerRecord(
            value=msgpack.packb(
                {
                    b"headers": {b"content-type": b"test1"},
                    b"endpoint": b"http://localhost:9000",
                    b"payload": (string.digits + string.ascii_letters).encode("utf-8"),
                    b"retry_time": int(time() - 90),
                }
            ),
            key="test_random_1",
            offset=1001,
            partition=0,
            topic="acapy.outbound_transport",
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
                    b"headers": {b"content-type": b"test1"},
                    b"endpoint": b"http://localhost:9000",
                    b"payload": (string.digits + string.ascii_letters).encode("utf-8"),
                    b"retry_time": int(time() + 300),
                }
            ),
            key="test_random_1",
            offset=1001,
            partition=0,
            topic="acapy.outbound_transport",
            timestamp=int(time()),
            timestamp_type=1,
            checksum=123232,
            serialized_key_size=123,
            serialized_value_size=12321,
            headers=[("test", b"test")],
        ),
    ]
}
offset_local_path = os.path.join(
    os.path.dirname(__file__),
    "test-partition-state-inbound_queue.json",
)


class TestRebalanceListener(AsyncTestCase):
    def setUp(self):
        self.test_partition = {
            TopicPartition(topic="topic1", partition=1),
            TopicPartition(topic="topic2", partition=0),
        }
        self.mock_consumer = async_mock.MagicMock(
            seek_to_beginning=async_mock.CoroutineMock(),
            seek=async_mock.CoroutineMock(),
            committed=async_mock.CoroutineMock(return_value=-1),
            commit=async_mock.CoroutineMock(),
        )
        self.listener = RebalanceListener(self.mock_consumer)

    async def test_on_partitions_revoked(self):
        self.listener.state = {TopicPartition(topic="topic1", partition=1): 10}
        await self.listener.on_partitions_revoked(self.test_partition)

    async def test_on_partitions_assigned_a(self):
        await self.listener.on_partitions_assigned(self.test_partition)

    async def test_on_partitions_assigned_b(self):
        mock_consumer = async_mock.MagicMock(
            seek_to_beginning=async_mock.CoroutineMock(),
            seek=async_mock.CoroutineMock(),
            committed=async_mock.CoroutineMock(return_value=1),
        )
        self.listener = RebalanceListener(mock_consumer)
        await self.listener.on_partitions_assigned(self.test_partition)

    async def test_get_last_offset(self):
        mock_consumer = async_mock.MagicMock(
            seek_to_beginning=async_mock.CoroutineMock(),
            seek=async_mock.CoroutineMock(),
            committed=async_mock.CoroutineMock(return_value=None),
        )
        self.listener = RebalanceListener(mock_consumer)
        await self.listener.get_last_offset(
            TopicPartition(topic="topic1", partition=1)
        ) == -1


class TestKafkaHandler(AsyncTestCase):
    def test_parse_connection_url(self):
        service = KafkaHandler(
            "localhost:8080,localhost:8081#username:password", "acapy"
        )
        assert service._host == "localhost:8080,localhost:8081"
        assert service.username == "username"
        assert service.password == "password"

    async def test_main(self):
        KafkaHandler.running = PropertyMock(side_effect=[True, True, False])
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
            KafkaHandler, "process_delivery", autospec=True
        ), async_mock.patch.object(
            KafkaHandler, "process_retries", autospec=True
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

    async def test_process_delivery(self):
        sentinel = PropertyMock(side_effect=[True, True, False])
        KafkaHandler.running = sentinel
        service = KafkaHandler("test", "acapy")
        with async_mock.patch.object(
            aiohttp.ClientSession,
            "post",
            async_mock.CoroutineMock(return_value=async_mock.MagicMock(status=200)),
        ), async_mock.patch.object(
            service, "process_retries", async_mock.CoroutineMock()
        ):
            mock_producer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                transaction=async_mock.MagicMock(),
                send=async_mock.CoroutineMock(),
            )

            mock_consumer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                subscribe=async_mock.CoroutineMock(),
                getmany=async_mock.CoroutineMock(
                    side_effect=[
                        test_msg_sets_a,
                        test_msg_sets_b,
                    ]
                ),
                seek_to_beginning=async_mock.CoroutineMock(),
                commit=async_mock.CoroutineMock(),
                committed=async_mock.CoroutineMock(),
            )
            service.consumer = mock_consumer
            service.producer = mock_producer
            await service.process_delivery()

    async def test_process_delivery_x(self):
        sentinel = PropertyMock(side_effect=[True, True, True, True, False])
        KafkaHandler.running = sentinel
        service = KafkaHandler("test", "acapy")
        with async_mock.patch.object(
            aiohttp.ClientSession,
            "post",
            async_mock.CoroutineMock(
                side_effect=[
                    async_mock.MagicMock(status=400),
                    aiohttp.ClientError,
                    asyncio.TimeoutError,
                ]
            ),
        ), async_mock.patch.object(
            service, "process_retries", async_mock.CoroutineMock()
        ):
            mock_producer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                transaction=async_mock.MagicMock(),
                send=async_mock.CoroutineMock(),
            )

            mock_consumer = async_mock.MagicMock(
                start=async_mock.CoroutineMock(),
                stop=async_mock.CoroutineMock(),
                subscribe=async_mock.CoroutineMock(),
                getmany=async_mock.CoroutineMock(
                    side_effect=[
                        OffsetOutOfRangeError({}),
                        test_msg_sets_d,
                        test_msg_sets_b,
                        test_msg_sets_b,
                    ]
                ),
                seek_to_beginning=async_mock.CoroutineMock(),
                commit=async_mock.CoroutineMock(),
                committed=async_mock.CoroutineMock(),
            )
            service.consumer = mock_consumer
            service.producer = mock_producer
            await service.process_delivery()

    async def test_process_retries(self):
        sentinel = PropertyMock(side_effect=[True, True, False])
        KafkaHandler.running = sentinel
        service = KafkaHandler("test", "acapy")
        service.retry_timedelay_s = 0.1
        mock_producer = async_mock.MagicMock(
            start=async_mock.CoroutineMock(),
            stop=async_mock.CoroutineMock(),
            transaction=async_mock.MagicMock(),
            send=async_mock.CoroutineMock(),
        )

        mock_consumer = async_mock.MagicMock(
            start=async_mock.CoroutineMock(),
            stop=async_mock.CoroutineMock(),
            subscribe=async_mock.CoroutineMock(),
            getmany=async_mock.CoroutineMock(
                side_effect=[
                    OffsetOutOfRangeError({}),
                    test_msg_sets_e,
                ]
            ),
            seek_to_beginning=async_mock.CoroutineMock(),
            commit=async_mock.CoroutineMock(),
            committed=async_mock.CoroutineMock(),
        )
        service.consumer_retry = mock_consumer
        service.producer = mock_producer
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
