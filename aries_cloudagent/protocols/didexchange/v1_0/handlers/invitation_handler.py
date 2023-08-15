"""Connect invitation handler under RFC 23 (DID exchange)."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ....out_of_band.v1_0.messages.invitation import InvitationMessage

from ..messages.problem_report import DIDXProblemReport, ProblemReportReason


class InvitationHandler(BaseHandler):
    """Handler class for connection invitation message under RFC 23 (DID exchange)."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle connection invitation under RFC 23 (DID exchange).

        Args:
            context: Request context
            responder: Responder callback
        """

        self._logger.debug(f"InvitationHandler called with context {context}")
        assert isinstance(context.message, InvitationMessage)

        report = DIDXProblemReport(
            description={
                "code": ProblemReportReason.INVITATION_NOT_ACCEPTED.value,
                "en": (
                    "Out-of-band invitations for DID exchange "
                    "cannot be submitted via agent messaging"
                ),
            }
        )

        # client likely needs to be using direct responses to receive the problem report
        await responder.send_reply(report)
