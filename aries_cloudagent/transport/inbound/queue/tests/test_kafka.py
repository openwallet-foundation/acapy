import asyncio
import msgpack
import os
import pytest
import random
import string

from asynctest import TestCase as AsyncTestCase, mock as async_mock, PropertyMock
from aiokafka.errors import OffsetOutOfRangeError
from aiokafka import TopicPartition, ConsumerRecord
from time import time

from .....config.settings import Settings
from .....core.in_memory.profile import InMemoryProfile

from ...manager import InboundTransportManager

from .. import kafka as test_module
from ..base import InboundQueueConfigurationError
from ..kafka import KafkaInboundQueue, RebalanceListener


ENDPOINT = "http://localhost:9000"
KEYNAME = "acapy.kafka_inbound_transport"


test_msg_sets_a = {
    TopicPartition("acapy.inbound_transport", 0): [
        ConsumerRecord(
            value=msgpack.packb(
                {
                    "host": "test1",
                    "remote": "http://localhost:9000",
                    "data": (string.digits + string.ascii_letters),
                    "transport_type": "http",
                }
            ),
            key="test_random_2",
            offset=1003,
            partition=0,
            topic="acapy.inbound_transport",
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
                    "host": "test1",
                    "remote": "http://localhost:9000",
                    "data": (string.digits + string.ascii_letters),
                    "transport_type": "http",
                }
            ),
            key="test_random_3",
            offset=1002,
            partition=0,
            topic="acapy.inbound_transport",
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
    TopicPartition("acapy.inbound_transport", 0): [
        ConsumerRecord(
            value=msgpack.packb(
                {
                    "host": "test1",
                    "remote": "http://localhost:9000",
                    "data": (string.digits + string.ascii_letters),
                    "transport_type": "ws",
                }
            ),
            key="test_random_1",
            offset=1001,
            partition=0,
            topic="acapy.inbound_transport",
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
    TopicPartition("acapy.inbound_transport", 0): [
        ConsumerRecord(
            value=msgpack.packb(
                {
                    "host": "test1",
                    "remote": "http://localhost:9000",
                    "data": (string.digits + string.ascii_letters),
                    "txn_id": "test123",
                    "transport_type": "http",
                }
            ),
            key="test_random_1",
            offset=1000,
            partition=0,
            topic="acapy.inbound_transport",
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
    TopicPartition("acapy.inbound_transport", 0): [
        ConsumerRecord(
            value=msgpack.packb(
                {
                    "host": "test2",
                    "remote": "http://localhost:9000",
                    "data": (string.digits + string.ascii_letters),
                    "txn_id": "test123",
                    "transport_type": "ws",
                }
            ),
            key="test_random_3",
            offset=1003,
            partition=0,
            topic="acapy.inbound_transport",
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
                    "host": "test3",
                    "remote": "http://localhost:9000",
                    "data": (string.digits + string.ascii_letters),
                    "txn_id": "test123",
                    "transport_type": "http",
                }
            ),
            key="test_random_4",
            offset=1004,
            partition=0,
            topic="acapy.inbound_transport",
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
    "acapy.inbound_transport": [
        ConsumerRecord(
            value=msgpack.packb(
                """{
                    "host": "test1",
                    "remote": "http://localhost:9000",
                    "data": (string.digits + string.ascii_letters),
                    "txn_id": "test123",
                    "transport_type": "http",
                }""".encode(
                    "utf-8"
                )
            ),
            key="test_random_1",
            offset=1000,
            partition=0,
            topic="acapy.inbound_transport",
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

    async def test_add_offset(self):
        self.listener = RebalanceListener(self.mock_consumer)
        await self.listener.add_offset(1, 10, "topic1")


class TestKafkaInbound(AsyncTestCase):
    def setUp(self):
        self.session = InMemoryProfile.test_session()
        self.profile = self.session.profile
        self.context = self.profile.context

    def test_sanitize_connection_url(self):
        self.profile.settings[
            "transport.inbound_queue"
        ] = "localhost:8080,localhost:8081#username:password"
        queue = KafkaInboundQueue(self.profile)
        assert queue.sanitize_connection_url() == "localhost:8080,localhost:8081"

    async def test_init(self):
        self.profile.settings["transport.inbound_queue"] = "connection"
        self.profile.settings["transport.inbound_queue_transports"] = [
            ("http", "0.0.0.0", "8002"),
            ("ws", "0.0.0.0", "8003"),
        ]
        with async_mock.patch(
            "aiokafka.AIOKafkaProducer.start",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaProducer.stop",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaProducer.transaction",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaProducer.send",
            async_mock.CoroutineMock(),
        ) as mock_send, async_mock.patch(
            "aiokafka.AIOKafkaProducer",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.start",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.stop",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.subscribe",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.getmany",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.seek_to_beginning",
            async_mock.CoroutineMock(),
        ) as mock_seek_to_beginning, async_mock.patch(
            "aiokafka.AIOKafkaConsumer",
            async_mock.MagicMock(),
        ):
            queue = KafkaInboundQueue(self.profile)
            queue.prefix == "acapy"
            queue.connection = "connection"
            assert str(queue)
            await queue.start_queue()
            await queue.stop_queue()

    def test_init_x(self):
        with pytest.raises(InboundQueueConfigurationError):
            KafkaInboundQueue(self.profile)

    async def test_close(self):
        self.profile.settings["transport.inbound_queue"] = "connection"
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
        ):
            queue = KafkaInboundQueue(self.profile)
            await queue.start_queue()
            queue.producer._closed = True
            await queue.close()

    async def test_receive_messages(self):
        self.profile.settings["transport.inbound_queue"] = "connection"
        mock_inbound_mgr = async_mock.MagicMock(
            create_session=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(receive=async_mock.CoroutineMock())
            ),
        )
        sentinel = PropertyMock(side_effect=[True, True, False])
        KafkaInboundQueue.RUNNING = sentinel
        queue = KafkaInboundQueue(self.profile)
        with async_mock.patch.object(
            test_module.asyncio, "get_event_loop", async_mock.MagicMock()
        ) as mock_get_event_loop, async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait, async_mock.patch.object(
            test_module.asyncio, "sleep", async_mock.CoroutineMock()
        ) as mock_sleep, async_mock.patch.object(
            test_module, "RebalanceListener", autospec=True
        ) as mock_rebalance_listener, async_mock.patch(
            "aiokafka.AIOKafkaProducer.start",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaProducer.stop",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaProducer.transaction",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaProducer.send",
            async_mock.CoroutineMock(),
        ) as mock_send, async_mock.patch(
            "aiokafka.AIOKafkaProducer",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.start",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.stop",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.subscribe",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.getmany",
            async_mock.CoroutineMock(side_effect=[test_msg_sets_a, test_msg_sets_b]),
        ) as mock_get_many, async_mock.patch(
            "aiokafka.AIOKafkaConsumer.seek_to_beginning",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer",
            async_mock.MagicMock(),
        ):
            mock_get_event_loop.return_value = async_mock.MagicMock(
                create_task=async_mock.MagicMock()
            )
            self.context.injector.bind_instance(
                InboundTransportManager, mock_inbound_mgr
            )
            sentinel = PropertyMock(side_effect=[True, True, False])
            KafkaInboundQueue.RUNNING = sentinel
            queue = KafkaInboundQueue(self.profile)
            await queue.start_queue()
            await queue.receive_messages()
        assert mock_get_many.call_count == 2
        assert mock_send.call_count == 0

    async def test_receive_messages_direct_response_a(self):
        self.profile.settings["plugin_config"] = {
            "kafka_inbound_queue": {
                "connection": "connection",
                "prefix": "acapy",
            }
        }
        mock_inbound_mgr = async_mock.MagicMock(
            create_session=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    receive=async_mock.CoroutineMock(),
                    wait_response=async_mock.CoroutineMock(
                        side_effect=[
                            b"test_response",
                            b"test_response",
                            "test_response",
                        ]
                    ),
                    profile=self.profile,
                )
            ),
        )
        with async_mock.patch.object(
            test_module.asyncio,
            "get_event_loop",
            async_mock.MagicMock(
                create_task=async_mock.MagicMock(
                    side_effect=[
                        async_mock.MagicMock(
                            done=async_mock.MagicMock(return_value=True),
                        ),
                    ]
                )
            ),
        ), async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait, async_mock.patch.object(
            test_module.asyncio, "sleep", async_mock.CoroutineMock()
        ) as mock_sleep, async_mock.patch.object(
            test_module, "RebalanceListener", autospec=True
        ) as mock_rebalance_listener, async_mock.patch(
            "aiokafka.AIOKafkaProducer.start",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaProducer.stop",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaProducer.transaction",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaProducer.send",
            async_mock.CoroutineMock(),
        ) as mock_send, async_mock.patch(
            "aiokafka.AIOKafkaProducer",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.start",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.stop",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.subscribe",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.getmany",
            async_mock.CoroutineMock(side_effect=[test_msg_sets_c, test_msg_sets_d]),
        ) as mock_get_many, async_mock.patch(
            "aiokafka.AIOKafkaConsumer.seek_to_beginning",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer",
            async_mock.MagicMock(),
        ):
            sentinel = PropertyMock(side_effect=[True, True, False])
            KafkaInboundQueue.RUNNING = sentinel
            queue = KafkaInboundQueue(self.profile)
            self.context.injector.bind_instance(
                InboundTransportManager, mock_inbound_mgr
            )
            await queue.start_queue()
            await queue.receive_messages()
        assert mock_get_many.call_count == 2
        assert mock_send.call_count == 3

    async def test_receive_messages_direct_response_b(self):
        self.profile.settings["plugin_config"] = {
            "kafka_inbound_queue": {
                "connection": "connection",
                "prefix": "acapy",
            }
        }
        self.profile.settings["emit_new_didcomm_mime_type"] = True
        mock_inbound_mgr = async_mock.MagicMock(
            create_session=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(
                    receive=async_mock.CoroutineMock(),
                    wait_response=async_mock.CoroutineMock(
                        side_effect=[
                            b"test_response",
                        ]
                    ),
                    profile=self.profile,
                )
            ),
        )
        with async_mock.patch.object(
            test_module.asyncio,
            "get_event_loop",
            async_mock.MagicMock(
                create_task=async_mock.MagicMock(
                    side_effect=[
                        async_mock.MagicMock(
                            done=async_mock.MagicMock(return_value=False),
                        ),
                    ]
                )
            ),
        ), async_mock.patch.object(
            test_module.asyncio, "wait", async_mock.CoroutineMock()
        ) as mock_wait, async_mock.patch.object(
            test_module.asyncio, "sleep", async_mock.CoroutineMock()
        ) as mock_sleep, async_mock.patch.object(
            test_module, "RebalanceListener", autospec=True
        ) as mock_rebalance_listener, async_mock.patch(
            "aiokafka.AIOKafkaProducer.start",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaProducer.stop",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaProducer.transaction",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaProducer.send",
            async_mock.CoroutineMock(),
        ) as mock_send, async_mock.patch(
            "aiokafka.AIOKafkaProducer",
            async_mock.MagicMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.start",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.stop",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.subscribe",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer.getmany",
            async_mock.CoroutineMock(
                side_effect=[
                    OffsetOutOfRangeError({}),
                    test_msg_sets_e,
                    test_msg_sets_c,
                ]
            ),
        ) as mock_get_many, async_mock.patch(
            "aiokafka.AIOKafkaConsumer.seek_to_beginning",
            async_mock.CoroutineMock(),
        ), async_mock.patch(
            "aiokafka.AIOKafkaConsumer",
            async_mock.MagicMock(),
        ):
            sentinel = PropertyMock(side_effect=[True, True, True, False])
            KafkaInboundQueue.RUNNING = sentinel
            queue = KafkaInboundQueue(self.profile)
            self.context.injector.bind_instance(
                InboundTransportManager, mock_inbound_mgr
            )
            await queue.start_queue()
            await queue.receive_messages()

    def test_parse_connection_url(self):
        self.profile.settings[
            "transport.inbound_queue"
        ] = "localhost:8080,localhost:8081#username:password"
        queue = KafkaInboundQueue(self.profile)
        assert queue.connection == "localhost:8080,localhost:8081"
        assert queue.username == "username"
        assert queue.password == "password"
