import asyncio

from asynctest import TestCase

from ..message import InboundMessage
from ..receipt import MessageReceipt


class TestInboundMessage(TestCase):
    async def test_wait_response(self):
        message = InboundMessage(
            payload="test",
            connection_id="conn_id",
            receipt=MessageReceipt(),
            session_id="session_id",
        )
        assert not message.processing_complete_event.is_set()
        message.dispatch_processing_complete()
        assert message.processing_complete_event.is_set()

        message = InboundMessage(
            payload="test",
            connection_id="conn_id",
            receipt=MessageReceipt(),
            session_id="session_id",
        )
        assert not message.processing_complete_event.is_set()
        task = message.wait_processing_complete()
        message.dispatch_processing_complete()
        await asyncio.wait_for(task, 1)
