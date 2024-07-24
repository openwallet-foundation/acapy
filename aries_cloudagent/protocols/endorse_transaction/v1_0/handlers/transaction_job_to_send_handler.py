"""Transaction Job to send handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from ..manager import TransactionManager, TransactionManagerError
from ..messages.transaction_job_to_send import TransactionJobToSend


class TransactionJobToSendHandler(BaseHandler):
    """Handler class for sending transaction jobs."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle transaction jobs.

        Args:
            context: Request context
            responder: Responder callback
        """

        self._logger.debug(f"TransactionJobToSendHandler called with context {context}")
        assert isinstance(context.message, TransactionJobToSend)

        if not context.connection_ready:
            raise HandlerException("No connection established")
        assert context.connection_record

        mgr = TransactionManager(context.profile)
        try:
            await mgr.set_transaction_their_job(
                context.message, context.connection_record
            )
        except TransactionManagerError:
            self._logger.exception("Error receiving transaction jobs")
