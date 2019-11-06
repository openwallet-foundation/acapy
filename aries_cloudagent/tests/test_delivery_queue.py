import asyncio
from unittest import mock, TestCase

from aries_cloudagent.delivery_queue import DeliveryQueue
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from aries_cloudagent import messaging
from aries_cloudagent.connections.models.diddoc import DIDDoc, PublicKey, PublicKeyType, Service
from .. import conductor as test_module
from ..admin.base_server import BaseAdminServer
from ..config.base_context import ContextBuilder
from ..config.injection_context import InjectionContext
from ..connections.models.connection_target import ConnectionTarget
from ..messaging.message_delivery import MessageDelivery
from ..messaging.serializer import MessageSerializer
from ..messaging.outbound_message import OutboundMessage
from ..messaging.protocol_registry import ProtocolRegistry
from ..transport.inbound.base import InboundTransportConfiguration
from ..transport.outbound.queue.base import BaseOutboundMessageQueue
from ..transport.outbound.queue.basic import BasicOutboundMessageQueue
from ..wallet.base import BaseWallet
from ..wallet.basic import BasicWallet


class TestDeliveryQueue(AsyncTestCase):

    async def test_message_add_and_check(self):
        queue = DeliveryQueue()

        t = ConnectionTarget(recipient_keys=["aaa"])
        msg = OutboundMessage("x", target=t)
        queue.add_message(msg)
        assert queue.has_message_for_key("aaa")

    async def test_message_add_not_false_check(self):
        queue = DeliveryQueue()

        t = ConnectionTarget(recipient_keys=["aaa"])
        msg = OutboundMessage("x", target=t)
        queue.add_message(msg)
        assert queue.has_message_for_key("bbb") is False

    async def test_message_add_get_by_key(self):
        queue = DeliveryQueue()

        t = ConnectionTarget(recipient_keys=["aaa"])
        msg = OutboundMessage("x", target=t)
        queue.add_message(msg)
        assert queue.has_message_for_key("aaa")
        assert queue.get_one_message_for_key("aaa") == msg
        assert queue.has_message_for_key("aaa") is False

    async def test_message_add_get_by_list(self):
        queue = DeliveryQueue()

        t = ConnectionTarget(recipient_keys=["aaa"])
        msg = OutboundMessage("x", target=t)
        queue.add_message(msg)
        assert queue.has_message_for_key("aaa")
        msg_list = [m for m in queue.inspect_all_messages_for_key("aaa")]
        assert queue.message_count_for_key("aaa") == 1
        assert len(msg_list) == 1
        assert msg_list[0] == msg
        queue.remove_message_for_key("aaa", msg)
        assert queue.has_message_for_key("aaa") is False

    async def test_message_ttl(self):
        queue = DeliveryQueue()

        t = ConnectionTarget(recipient_keys=["aaa"])
        msg = OutboundMessage("x", target=t)
        queue.add_message(msg)
        assert queue.has_message_for_key("aaa")
        queue.expire_messages(ttl=-10)
        assert queue.has_message_for_key("aaa") is False

    async def test_count_zero_with_no_items(self):
        queue = DeliveryQueue()
        assert queue.message_count_for_key("aaa") == 0
