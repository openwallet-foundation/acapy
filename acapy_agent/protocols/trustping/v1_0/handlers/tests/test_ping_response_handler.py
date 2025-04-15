import pytest
import pytest_asyncio

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt
from ......utils.testing import create_test_profile
from ...handlers.ping_response_handler import PingResponseHandler
from ...messages.ping_response import PingResponse


@pytest_asyncio.fixture
async def request_context():
    yield RequestContext.test_context(await create_test_profile())


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
