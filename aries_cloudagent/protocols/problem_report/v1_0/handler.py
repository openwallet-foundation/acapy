"""Generic problem report handler."""

from ....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from .message import ProblemReport


class ProblemReportHandler(BaseHandler):
    """Problem report handler class."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle problem report message.

        Args:
            context: Request context
            responder: Responder used to reply

        """
        self._logger.debug("ProblemReportHandler called with context %s", context)
        assert isinstance(context.message, ProblemReport)

        self._logger.info(
            "Received problem report from: %s, %r",
            context.message_receipt.sender_did,
            context.message,
        )

        await context.profile.notify(
            "acapy::problem_report", context.message.serialize()
        )
