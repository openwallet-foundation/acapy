import asyncio
import msgpack
import os
import pytest
import random
import string

from asynctest import TestCase as AsyncTestCase, mock as async_mock, PropertyMock
from aiokafka.errors import OffsetOutOfRangeError
from aiokafka.structs import TopicPartition
from collections import Counter

from .....config.settings import Settings
from .....core.in_memory.profile import InMemoryProfile

from ...manager import InboundTransportManager

from .. import kafka as test_module
from ..base import InboundQueueConfigurationError, InboundQueueError
from ..kafka import KafkaInboundQueue, LocalState, RebalanceListener


ENDPOINT = "http://localhost:9000"
KEYNAME = "acapy.kafka_inbound_transport"


test_msg_sets_a = {
    "test1": [
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    "host": "test1",
                    "remote": "http://localhost:9000",
                    "data": (string.digits + string.ascii_letters).encode(
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
                    "host": "test1",
                    "remote": "http://localhost:9000",
                    "data": (string.digits + string.ascii_letters).encode(
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
    "test3": [
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    "host": "test1",
                    "remote": "http://localhost:9000",
                    "data": (string.digits + string.ascii_letters).encode(
                        encoding="utf-8"
                    ),
                }
            ),
            key="test_random_1",
            offsets=1001,
        )
    ]
}

test_msg_sets_c = {
    "test1": [
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    "host": "test1",
                    "remote": "http://localhost:9000",
                    "data": bytes(range(0, 256)),
                    "txn_id": "test123",
                    "transport_type": "http",
                }
            ),
            key="test_random_1",
            offsets=1000,
        )
    ]
}

test_msg_sets_d = {
    "test2": [
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    "host": "test2",
                    "remote": "http://localhost:9000",
                    "data": bytes(range(0, 256)),
                    "txn_id": "test123",
                    "transport_type": "ws",
                }
            ),
            key="test_random_3",
            offsets=1003,
        ),
        async_mock.MagicMock(
            value=msgpack.packb(
                {
                    "host": "test3",
                    "remote": "http://localhost:9000",
                    "data": bytes(range(0, 256)),
                    "txn_id": "test123",
                    "transport_type": "http",
                }
            ),
            key="test_random_4",
            offsets=1004,
        ),
    ]
}

test_msg_sets_e = {
    "test1": [
        async_mock.MagicMock(
            value=msgpack.packb(
                """{
                    "host": "test1",
                    "remote": "http://localhost:9000",
                    "data": bytes(range(0, 256)),
                    "txn_id": "test123",
                    "transport_type": "http",
                }""".encode(
                    "utf-8"
                )
            ),
            key="test_random_1",
            offsets=1000,
        )
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
        )
        self.mock_local_state = async_mock.MagicMock(
            dump_local_state=async_mock.MagicMock(),
            load_local_state=async_mock.MagicMock(),
            get_last_offset=async_mock.MagicMock(return_value=-1),
        )
        self.listener = RebalanceListener(self.mock_consumer, self.mock_local_state)

    async def test_on_partitions_revoked(self):
        await self.listener.on_partitions_revoked(self.test_partition)

    async def test_on_partitions_assigned_a(self):
        await self.listener.on_partitions_assigned(self.test_partition)

    async def test_on_partitions_assigned_b(self):
        self.mock_local_state = async_mock.MagicMock(
            dump_local_state=async_mock.MagicMock(),
            load_local_state=async_mock.MagicMock(),
            get_last_offset=async_mock.MagicMock(return_value=1),
        )
        self.listener = RebalanceListener(self.mock_consumer, self.mock_local_state)
        await self.listener.on_partitions_assigned(self.test_partition)


class TestLocalState(AsyncTestCase):
    def setUp(self):
        self.local_state = LocalState()
        self.local_state.OFFSET_LOCAL_FILE = offset_local_path
        assert self.local_state._counts == {}
        assert self.local_state._offsets == {}
        test_partition = {
            TopicPartition(topic="topic1", partition=1),
            TopicPartition(topic="topic2", partition=0),
        }
        self.local_state.load_local_state(test_partition)
        assert self.local_state._counts != {}
        assert self.local_state._offsets != {}

    def test_dump_local_state(self):
        self.local_state.dump_local_state()

    def test_utility_functions(self):
        counts = Counter()
        counts[123] += 1
        counts[456] += 1
        self.local_state.add_counts(
            TopicPartition(topic="topic1", partition=1), counts, 100
        )
        assert (
            self.local_state.get_last_offset(
                TopicPartition(topic="topic1", partition=1)
            )
            == 100
        )
        assert (
            self.local_state._counts[TopicPartition(topic="topic1", partition=1)]
            != Counter()
        )
        assert (
            self.local_state._offsets[TopicPartition(topic="topic1", partition=1)] != -1
        )
        self.local_state.discard_state([TopicPartition(topic="topic1", partition=1)])
        assert (
            self.local_state._counts[TopicPartition(topic="topic1", partition=1)]
            == Counter()
        )
        assert (
            self.local_state._offsets[TopicPartition(topic="topic1", partition=1)] == -1
        )


class TestKafkaInbound(AsyncTestCase):
    def setUp(self):
        self.session = InMemoryProfile.test_session()
        self.profile = self.session.profile
        self.context = self.profile.context

    async def test_init(self):
        self.profile.settings["transport.inbound_queue"] = "connection"
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
            await queue.start()
            await queue.stop()

    def test_init_x(self):
        with pytest.raises(InboundQueueConfigurationError):
            KafkaInboundQueue(self.profile)

    async def test_receive_messages(self):
        self.profile.settings["transport.inbound_queue"] = "connection"
        mock_inbound_mgr = async_mock.MagicMock(
            create_session=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(receive=async_mock.CoroutineMock())
            ),
        )
        with async_mock.patch.object(
            asyncio, "get_event_loop", async_mock.MagicMock()
        ) as mock_get_event_loop, async_mock.patch.object(
            test_module, "RebalanceListener", autospec=True
        ) as mock_rebalance_listener, async_mock.patch.object(
            test_module, "LocalState", autospec=True
        ) as mock_local_state, async_mock.patch(
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
            await queue.start()
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
            asyncio, "get_event_loop", async_mock.MagicMock()
        ) as mock_get_event_loop, async_mock.patch.object(
            test_module, "RebalanceListener", autospec=True
        ) as mock_rebalance_listener, async_mock.patch.object(
            test_module, "LocalState", autospec=True
        ) as mock_local_state, async_mock.patch(
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
            mock_get_event_loop.return_value = async_mock.MagicMock(
                create_task=async_mock.MagicMock(
                    side_effect=[
                        async_mock.MagicMock(
                            done=async_mock.MagicMock(return_value=True),
                        ),
                    ]
                )
            )
            self.context.injector.bind_instance(
                InboundTransportManager, mock_inbound_mgr
            )
            sentinel = PropertyMock(side_effect=[True, True, False])
            KafkaInboundQueue.RUNNING = sentinel
            queue = KafkaInboundQueue(self.profile)
            await queue.start()
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
            asyncio, "get_event_loop", async_mock.MagicMock()
        ) as mock_get_event_loop, async_mock.patch.object(
            test_module, "RebalanceListener", autospec=True
        ) as mock_rebalance_listener, async_mock.patch.object(
            test_module, "LocalState", autospec=True
        ) as mock_local_state, async_mock.patch(
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
            mock_get_event_loop.return_value = async_mock.MagicMock(
                create_task=async_mock.MagicMock(
                    side_effect=[
                        async_mock.MagicMock(
                            done=async_mock.MagicMock(return_value=False),
                        ),
                    ]
                )
            )
            self.context.injector.bind_instance(
                InboundTransportManager, mock_inbound_mgr
            )
            sentinel = PropertyMock(side_effect=[True, True, True, False])
            KafkaInboundQueue.RUNNING = sentinel
            queue = KafkaInboundQueue(self.profile)
            await queue.start()
            await queue.receive_messages()

    async def test_save_state_every_second(self):
        self.profile.settings["transport.inbound_queue"] = "connection"
        sentinel = PropertyMock(side_effect=[True, True, True, False])
        KafkaInboundQueue.RUNNING = sentinel
        queue = KafkaInboundQueue(self.profile)
        with async_mock.patch.object(
            test_module, "LocalState", autospec=True
        ) as mock_local_state, async_mock.patch.object(
            test_module.asyncio,
            "sleep",
            async_mock.CoroutineMock(
                side_effect=[None, None, test_module.asyncio.CancelledError]
            ),
        ):
            await queue.save_state_every_second(mock_local_state)
        assert mock_local_state.dump_local_state.call_count == 2
