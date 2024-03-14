"""Rotate problem report handler."""

from .....messaging.base_handler import BaseHandler
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from ..manager import DIDRotateManager
from ..messages.problem_report import RotateProblemReport


class ProblemReportHandler(BaseHandler):
    """Message handler class for rotate message."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle rotate problem report message.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug("ProblemReportHandler called with context %s", context)
        assert isinstance(context.message, RotateProblemReport)

        problem_report = context.message

        profile = context.profile
        did_rotate_mgr = DIDRotateManager(profile)

        await did_rotate_mgr.receive_problem_report(problem_report)
