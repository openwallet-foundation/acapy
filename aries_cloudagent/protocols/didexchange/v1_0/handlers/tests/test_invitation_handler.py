import pytest

from aries_cloudagent.messaging.base_handler import HandlerException
from aries_cloudagent.messaging.request_context import RequestContext
from aries_cloudagent.messaging.responder import MockResponder
from aries_cloudagent.transport.inbound.receipt import MessageReceipt

from ...handlers.invitation_handler import Conn23InvitationHandler
from ...messages.invitation import Conn23Invitation
from ...messages.problem_report import ProblemReport, ProblemReportReason


@pytest.fixture()
def request_context() -> RequestContext:
    ctx = RequestContext()
    ctx.message_receipt = MessageReceipt()
    yield ctx


class TestConn23InvitationHandler:
    @pytest.mark.asyncio
    async def test_problem_report(self, request_context):
        request_context.message = Conn23Invitation()
        handler = Conn23InvitationHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert (
            isinstance(result, ProblemReport)
            and result.problem_code == ProblemReportReason.INVITATION_NOT_ACCEPTED
        )
        assert not target
