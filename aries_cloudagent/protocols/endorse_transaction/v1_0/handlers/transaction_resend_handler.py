"""Transaction resend handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..manager import TransactionManager, TransactionManagerError
from ..messages.transaction_resend import TransactionResend


class TransactionResendHandler(BaseHandler):
    """Handler class for transaction resend."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle transaction resend.

        Args:
            context: Request context
            responder: Responder callback
        """

        self._logger.debug(f"TransactionResendHandler called with context {context}")
        assert isinstance(context.message, TransactionResend)

        mgr = TransactionManager(context, context.profile)
        try:
            await mgr.receive_transaction_resend(context.message)
        except TransactionManagerError:
            self._logger.exception("Error receiving resend transaction request")
