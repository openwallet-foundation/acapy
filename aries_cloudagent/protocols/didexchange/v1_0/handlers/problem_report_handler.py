"""Problem report handler for DID Exchange."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from ..manager import DIDXManager, DIDXManagerError
from ..messages.problem_report import DIDXProblemReport


class DIDXProblemReportHandler(BaseHandler):
    """Handler class for DID Exchange problem report messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle problem report message."""
        self._logger.debug(f"DIDXProblemReportHandler called with context {context}")
        assert isinstance(context.message, DIDXProblemReport)

        self._logger.info("Received problem report: %s", context.message.description)
        profile = context.profile
        mgr = DIDXManager(profile)
        try:
            if context.connection_record:
                await mgr.receive_problem_report(
                    context.connection_record, context.message
                )
            else:
                raise HandlerException("No connection established for problem report")
        except DIDXManagerError:
            # Unrecognized problem report code
            self._logger.exception("Error receiving DID Exchange problem report")
