"""Cancel transaction request handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..manager import TransactionManager


class TransactionCancelHandler(BaseHandler):
    """Handler class for Cancel transaction request."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle cancel transaction request.

        Args:
            context: Request context
            responder: Responder callback
        """

        mgr = TransactionManager(context)
        await mgr.receive_cancel_transaction(context.message)
