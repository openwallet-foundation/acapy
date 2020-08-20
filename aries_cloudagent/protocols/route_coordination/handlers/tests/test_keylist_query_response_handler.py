import pytest
from asynctest import (
    mock as async_mock,
    TestCase as AsyncTestCase,
)

from .....messaging.request_context import RequestContext
from .....messaging.responder import MockResponder
from .....transport.inbound.receipt import MessageReceipt

from ...messages.keylist import KeylistQueryResponse
from ...handlers import keylist_query_response_handler as handler


class TestKeylistQueryResponseHandler(AsyncTestCase):
    async def test_called(self):
        request_context = RequestContext()
        request_context.message_receipt = MessageReceipt()
        request_context.connection_record = async_mock.MagicMock()
        request_context.message = KeylistQueryResponse()
        request_context.connection_ready = True
        handler_inst = handler.KeylistQueryResponseHandler()
        responder = MockResponder()
        await handler_inst.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 0
