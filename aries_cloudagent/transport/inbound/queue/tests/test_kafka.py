import asyncio
import msgpack
import pytest
import random
import string

from asynctest import TestCase as AsyncTestCase, mock as async_mock, PropertyMock

from .....config.settings import Settings
from .....core.in_memory.profile import InMemoryProfile

from ...manager import InboundTransportManager

from .. import kafka as test_module
from ..base import InboundQueueConfigurationError, InboundQueueError
from ..kafka import KafkaInboundQueue


ENDPOINT = "http://localhost:9000"
KEYNAME = "acapy.kafka_inbound_transport"


def mock_blpop(response_reqd=False):
    if not response_reqd:
        return msgpack.packb(
            {
                "host": "test1",
                "remote": "http://localhost:9000",
                "data": (string.digits + string.ascii_letters).encode(encoding="utf-8"),
            }
        )
    else:
        index = round(random.random())
        if index == 0:
            return msgpack.packb(
                {
                    "host": "test2",
                    "remote": "http://localhost:9000",
                    "data": bytes(range(0, 256)),
                    "txn_id": "test123",
                    "transport_type": "http",
                }
            )
        else:
            return msgpack.packb(
                {
                    "host": "test2",
                    "remote": "http://localhost:9000",
                    "data": bytes(range(0, 256)),
                    "txn_id": "test123",
                    "transport_type": "ws",
                }
            )


def decode_func(value):
    return value.decode("utf-8")


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
        ) as mock_get_many, async_mock.patch(
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

    def test_init_x(self):
        with pytest.raises(InboundQueueConfigurationError):
            KafkaInboundQueue(self.profile)

    async def test_receive_message(self):
        self.profile.settings["transport.inbound_queue"] = "connection"
        mock_inbound_mgr = async_mock.MagicMock(
            create_session=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(receive=async_mock.CoroutineMock())
            ),
        )
        with async_mock.patch.object(
            asyncio, "get_event_loop", async_mock.MagicMock()
        ) as mock_get_event_loop, async_mock.patch(
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
        ) as mock_send, async_mock.patch(
            "aiokafka.AIOKafkaConsumer.seek_to_beginning",
            async_mock.CoroutineMock(),
        ) as mock_send, async_mock.patch(
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
