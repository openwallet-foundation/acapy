import pytest

from ....messaging.base_handler import HandlerException
from ....messaging.request_context import RequestContext
from ....messaging.responder import MockResponder
from ....transport.inbound.receipt import MessageReceipt

from ..handler import ProblemReportHandler
from ..message import ProblemReport


@pytest.fixture()
def request_context() -> RequestContext:
    ctx = RequestContext()
    yield ctx


class TestPingHandler:
    @pytest.mark.asyncio
    async def test_problem_report(self, request_context):
        request_context.message_receipt = MessageReceipt()
        request_context.message = ProblemReport()
        request_context.connection_ready = True
        handler = ProblemReportHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 0
        hooks = responder.webhooks
        assert len(hooks) == 1
        assert hooks[0] == ("problem_report", request_context.message.serialize())
