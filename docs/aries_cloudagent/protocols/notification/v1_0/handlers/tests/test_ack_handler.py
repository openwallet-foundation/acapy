from unittest import mock
from unittest import IsolatedAsyncioTestCase

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from ...messages.ack import V10Ack

from .. import ack_handler as test_module


class TestNotificationAckHandler(IsolatedAsyncioTestCase):
    async def test_called(self):
        request_context = RequestContext.test_context()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = mock.MagicMock()

        request_context.message = V10Ack(status="OK")
        handler = test_module.V10AckHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)
