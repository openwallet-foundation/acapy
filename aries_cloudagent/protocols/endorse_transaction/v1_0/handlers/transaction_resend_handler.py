"""Transaction resend handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..manager import TransactionManager


class TransactionResendHandler(BaseHandler):
    """Handler class for transaction resend."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle transaction resend.

        Args:
            context: Request context
            responder: Responder callback
        """

        mgr = TransactionManager(context)
        await mgr.receive_transaction_resend(context.message)
