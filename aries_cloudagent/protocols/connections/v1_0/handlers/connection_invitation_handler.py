"""Connect invitation handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ....problem_report.v1_0.message import ProblemReport

from ..messages.connection_invitation import ConnectionInvitation
from ..messages.problem_report_reason import ProblemReportReason


class ConnectionInvitationHandler(BaseHandler):
    """Handler class for connection invitations."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle connection invitation.

        Args:
            context: Request context
            responder: Responder callback
        """
        self._logger.debug(f"ConnectionInvitationHandler called with context {context}")
        assert isinstance(context.message, ConnectionInvitation)

        explain_ltxt = "Connection invitations cannot be submitted via agent messaging"
        report = ProblemReport(
            explain_ltxt=explain_ltxt,
            problem_items=[
                {ProblemReportReason.INVITATION_NOT_ACCEPTED.value: explain_ltxt}
            ],
        )

        # client likely needs to be using direct responses to receive the problem report
        await responder.send_reply(report)
