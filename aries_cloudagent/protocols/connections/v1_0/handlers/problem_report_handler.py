"""Problem report handler for Connection Protocol."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from ..manager import ConnectionManager, ConnectionManagerError
from ..messages.problem_report import ConnectionProblemReport


class ConnectionProblemReportHandler(BaseHandler):
    """Handler class for Connection problem report messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle problem report message."""
        self._logger.debug(
            f"ConnectionProblemReportHandler called with context {context}"
        )
        assert isinstance(context.message, ConnectionProblemReport)

        self._logger.info(f"Received problem report: {context.message.problem_code}")
        profile = context.profile
        mgr = ConnectionManager(profile)
        try:
            if context.connection_record:
                await mgr.receive_problem_report(
                    context.connection_record, context.message
                )
            else:
                raise HandlerException("No connection established for problem report")
        except ConnectionManagerError:
            # Unrecognized problem report code
            self._logger.exception("Error receiving Connection problem report")
