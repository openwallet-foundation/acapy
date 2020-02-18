import asyncio
from unittest import mock, TestCase

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ....connections.models.connection_target import ConnectionTarget
from ....transport.outbound.message import OutboundMessage

from ..delivery_queue import DeliveryQueue


class TestDeliveryQueue(AsyncTestCase):
    async def test_message_add_and_check(self):
        queue = DeliveryQueue()

        t = ConnectionTarget(recipient_keys=["aaa"])
        msg = OutboundMessage(payload="x", target=t)
        queue.add_message(msg)
        assert queue.has_message_for_key("aaa")

    async def test_message_add_not_false_check(self):
        queue = DeliveryQueue()

        t = ConnectionTarget(recipient_keys=["aaa"])
        msg = OutboundMessage(payload="x", target=t)
        queue.add_message(msg)
        assert queue.has_message_for_key("bbb") is False

    async def test_message_add_get_by_key(self):
        queue = DeliveryQueue()

        t = ConnectionTarget(recipient_keys=["aaa"])
        msg = OutboundMessage(payload="x", target=t)
        queue.add_message(msg)
        assert queue.has_message_for_key("aaa")
        assert queue.get_one_message_for_key("aaa") == msg
        assert queue.has_message_for_key("aaa") is False

    async def test_message_add_get_by_list(self):
        queue = DeliveryQueue()

        t = ConnectionTarget(recipient_keys=["aaa"])
        msg = OutboundMessage(payload="x", target=t)
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
        msg = OutboundMessage(payload="x", target=t)
        queue.add_message(msg)
        assert queue.has_message_for_key("aaa")
        queue.expire_messages(ttl=-10)
        assert queue.has_message_for_key("aaa") is False

    async def test_count_zero_with_no_items(self):
        queue = DeliveryQueue()
        assert queue.message_count_for_key("aaa") == 0
