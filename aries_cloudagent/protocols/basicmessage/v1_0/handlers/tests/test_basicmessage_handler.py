from unittest import mock

import pytest

from ......core.event_bus import EventBus, MockEventBus, Event
from ......messaging.decorators.localization_decorator import LocalizationDecorator
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
        mock_event_bus = MockEventBus()
        request_context.profile.context.injector.bind_instance(EventBus, mock_event_bus)
        request_context.connection_record = mock.MagicMock()
        test_message_content = "http://aries.ca/hello"
        request_context.message = BasicMessage(content=test_message_content)
        request_context.connection_ready = True
        handler = BasicMessageHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 0
        assert len(mock_event_bus.events) == 1
        assert mock_event_bus.events[0] == (
            request_context.profile,
            Event(
                "acapy::basicmessage::received",
                {
                    "connection_id": request_context.connection_record.connection_id,
                    "message_id": request_context.message._id,
                    "content": test_message_content,
                    "state": "received",
                    "sent_time": request_context.message.sent_time,
                },
            ),
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
            content=test_message_content,
            localization=LocalizationDecorator(locale="en-CA"),
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
