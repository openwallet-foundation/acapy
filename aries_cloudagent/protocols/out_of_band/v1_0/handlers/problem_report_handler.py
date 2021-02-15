"""OOB Problem Report Message Handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..manager import OutOfBandManager, OutOfBandManagerError
from ..messages.problem_report import ProblemReport


class OOBProblemReportMessageHandler(BaseHandler):
    """
    Handler class for OOB Problem Report Message.

    Updates the ConnRecord Metadata state.
    """

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        OOB Problem Report Message Handler.

        Args:
            context: Request context
            responder: Responder callback
        """
        self._logger.debug(
            f"OOBProblemReportMessageHandler called with context {context}"
        )
        assert isinstance(context.message, ProblemReport)

        session = await context.session()
        mgr = OutOfBandManager(session)
        try:
            await mgr.receive_problem_report(
                problem_report=context.message,
                receipt=context.message_receipt,
                conn_record=context.connection_record,
            )
        except OutOfBandManagerError:
            self._logger.exception("Error processing Problem Report message")
