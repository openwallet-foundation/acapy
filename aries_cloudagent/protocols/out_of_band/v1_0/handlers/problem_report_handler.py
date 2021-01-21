"""OOB Problem Report Message Handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..manager import OutOfBandManager, OutOfBandManagerError
from ..messages.reuse import HandshakeReuse


class OOBProblemReportMessageHandler(BaseHandler):
    """Handler class for OOB Problem Report Message to update the state of the \
    ConnReuseMessage Record to STATE_NOT_ACCEPTED."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        OOB Problem Report Message Handler.

        Args:
            context: Request context
            responder: Responder callback
        """
        self._logger.debug(f"OOBProblemReportMessageHandler called with context {context}")
        assert isinstance(context.message, HandshakeReuse)

        session = await context.session()
        mgr = OutOfBandManager(session)
        try:
            await mgr.receive_problem_report(
                problem_report=context.message,
                reciept=context.message_receipt,
                conn_record=context.connection_record,
            )
        except OutOfBandManagerError:
            self._logger.exception("Error processing Problem Report message")
