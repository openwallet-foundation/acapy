"""Connect invitation handler under RFC 23 (DID exchange)."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..messages.invitation import Conn23Invitation
from ..messages.problem_report import ProblemReport, ProblemReportReason


class Conn23InvitationHandler(BaseHandler):
    """Handler class for connection invitations under RFC 23 (DID exchange)."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle connection invitation under RFC 23 (DID exchange).

        Args:
            context: Request context
            responder: Responder callback
        """

        self._logger.debug(f"Conn23InvitationHandler called with context {context}")
        assert isinstance(context.message, Conn23Invitation)

        report = ProblemReport(
            problem_code=ProblemReportReason.INVITATION_NOT_ACCEPTED,
            explain="Connection invitations cannot be submitted via agent messaging",
        )
        # client likely needs to be using direct responses to receive the problem report
        await responder.send_reply(report)
