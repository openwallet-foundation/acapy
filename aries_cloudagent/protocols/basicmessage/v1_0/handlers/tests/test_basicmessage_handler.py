import pytest
from unittest import mock

from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder

from ...handlers.basicmessage_handler import BasicMessageHandler
from ...messages.basicmessage import BasicMessage


@pytest.fixture()
def request_context() -> RequestContext:
    yield RequestContext.test_context()


class TestBasicMessageHandler:
    @pytest.mark.asyncio
    async def test_basic_message(self, request_context):
        request_context.connection_record = mock.MagicMock()
        test_message_content = "http://aries.ca/hello"
        request_context.message = BasicMessage(content=test_message_content)
        request_context.connection_ready = True
        handler = BasicMessageHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 0
        hooks = responder.webhooks
        assert len(hooks) == 1
        assert hooks[0] == (
            "basicmessages",
            {
                "connection_id": request_context.connection_record.connection_id,
                "message_id": request_context.message._id,
                "content": test_message_content,
                "state": "received",
            },
        )

    @pytest.mark.asyncio
    async def test_basic_message_response(self, request_context):
        request_context.update_settings({"debug.auto_respond_messages": True})
        request_context.connection_record = mock.MagicMock()
        request_context.default_label = "agent"
        test_message_content = "hello"
        request_context.message = BasicMessage(content=test_message_content)
        request_context.connection_ready = True
        handler = BasicMessageHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 1
        reply, target = messages[0]
        assert isinstance(reply, BasicMessage)
        assert reply._thread_id == request_context.message._thread_id
        assert not target

    @pytest.mark.asyncio
    async def test_basic_message_response_reply_with(self, request_context):
        request_context.update_settings({"debug.auto_respond_messages": False})
        request_context.connection_record = mock.MagicMock()
        request_context.default_label = "agent"
        test_message_content = "Reply with: g'day"
        request_context.message = BasicMessage(
            content=test_message_content, localization="en-CA"
        )
        request_context.connection_ready = True
        handler = BasicMessageHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 1
        reply, target = messages[0]
        assert isinstance(reply, BasicMessage)
        assert reply._thread_id == request_context.message._thread_id
        assert not target
