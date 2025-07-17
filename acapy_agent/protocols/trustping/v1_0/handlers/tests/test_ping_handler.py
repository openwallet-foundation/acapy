import pytest
import pytest_asyncio

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt
from ......utils.testing import create_test_profile
from ...handlers.ping_handler import PingHandler
from ...messages.ping import Ping
from ...messages.ping_response import PingResponse


@pytest_asyncio.fixture
async def request_context():
    yield RequestContext.test_context(await create_test_profile())


class TestPingHandler:
    @pytest.mark.asyncio
    async def test_ping(self, request_context):
        request_context.message_receipt = MessageReceipt()
        request_context.message = Ping(response_requested=False)
        request_context.settings["debug.monitor_ping"] = True
        request_context.connection_ready = True
        handler = PingHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 0

    @pytest.mark.asyncio
    async def test_ping_not_ready(self, request_context):
        request_context.message_receipt = MessageReceipt()
        request_context.message = Ping(response_requested=False)
        request_context.connection_ready = False
        handler = PingHandler()
        responder = MockResponder()
        assert not await handler.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 0

    @pytest.mark.asyncio
    async def test_ping_response(self, request_context):
        request_context.message_receipt = MessageReceipt()
        request_context.message = Ping(response_requested=True)
        request_context.connection_ready = True
        handler = PingHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert isinstance(result, PingResponse)
        assert result._thread_id == request_context.message._thread_id
        assert not target
