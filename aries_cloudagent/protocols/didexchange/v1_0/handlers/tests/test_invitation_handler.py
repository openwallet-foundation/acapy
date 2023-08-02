import pytest

from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt

from .....out_of_band.v1_0.messages.invitation import InvitationMessage

from ...handlers.invitation_handler import InvitationHandler
from ...messages.problem_report import DIDXProblemReport, ProblemReportReason
from ......wallet.did_method import DIDMethods


@pytest.fixture()
def request_context() -> RequestContext:
    ctx = RequestContext.test_context()
    ctx.injector.bind_instance(DIDMethods, DIDMethods())
    ctx.message_receipt = MessageReceipt()
    yield ctx


class TestDIDXInvitationHandler:
    @pytest.mark.asyncio
    async def test_problem_report(self, request_context):
        request_context.message = InvitationMessage()
        handler = InvitationHandler()
        responder = MockResponder()
        await handler.handle(request_context, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert (
            isinstance(result, DIDXProblemReport)
            and result.description
            and (
                result.description["code"]
                == ProblemReportReason.INVITATION_NOT_ACCEPTED.value
            )
        )
        assert not target
