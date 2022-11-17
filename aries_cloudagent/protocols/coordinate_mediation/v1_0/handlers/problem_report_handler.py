"""Coordinate mediation problem report message handler."""

from .....messaging.base_handler import BaseHandler
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder

from ..messages.problem_report import CMProblemReport


class CMProblemReportHandler(BaseHandler):
    """
    Handler class for Coordinate Mediation Problem Report Message.

    Updates the ConnRecord Metadata state.
    """

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Coordinate mediation problem report message handler.

        Args:
            context: Request context
            responder: Responder callback
        """
        self._logger.debug(f"CMProblemReportHandler called with context {context}")
        assert isinstance(context.message, CMProblemReport)
        self._logger.error(
            f"Received coordinate-mediation problem report message: {context.message}"
        )
