"""Problem report handler."""

from .....messaging.base_handler import BaseHandler
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder

from ..messages.problem_report import ProblemReport


class ProblemReportHandler(BaseHandler):
    """Message handler class for rotate message."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle rotate message.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug("ProblemReportHandler called with context %s", context)
        assert isinstance(context.message, ProblemReport)
