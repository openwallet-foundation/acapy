import pytest
import pytest_asyncio

from .....core.event_bus import EventBus, MockEventBus
from .....messaging.request_context import RequestContext
from .....messaging.responder import MockResponder
from .....transport.inbound.receipt import MessageReceipt
from .....utils.testing import create_test_profile
from ..handler import ProblemReportHandler
from ..message import ProblemReport


@pytest_asyncio.fixture
async def request_context():
    yield RequestContext.test_context(await create_test_profile())


class TestPingHandler:
    @pytest.mark.asyncio
    async def test_problem_report(self, request_context):
        mock_event_bus = MockEventBus()
        request_context.profile.context.injector.bind_instance(EventBus, mock_event_bus)

        request_context.message_receipt = MessageReceipt()
        request_context.message = ProblemReport(description={"code": "error-code"})
        request_context.connection_ready = True
        handler = ProblemReportHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 0
        assert len(mock_event_bus.events) == 1
        (profile, event) = mock_event_bus.events[0]
        assert profile == request_context.profile
        assert event.topic == "acapy::problem_report"
        assert event.payload == request_context.message.serialize()
