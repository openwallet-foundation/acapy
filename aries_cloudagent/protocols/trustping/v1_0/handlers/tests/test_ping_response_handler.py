import pytest

from aries_cloudagent.messaging.base_handler import HandlerException
from aries_cloudagent.messaging.request_context import RequestContext
from aries_cloudagent.messaging.responder import MockResponder
from aries_cloudagent.transport.inbound.receipt import MessageReceipt

from ...handlers.ping_response_handler import PingResponseHandler
from ...messages.ping_response import PingResponse


@pytest.fixture()
def request_context() -> RequestContext:
    ctx = RequestContext.test_context()
    yield ctx


class TestPingResponseHandler:
    @pytest.mark.asyncio
    async def test_ping_response(self, request_context):
        request_context.message_receipt = MessageReceipt()
        request_context.message = PingResponse()
        request_context.settings["debug.monitor_ping"] = True
        request_context.connection_ready = True
        handler = PingResponseHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 0
