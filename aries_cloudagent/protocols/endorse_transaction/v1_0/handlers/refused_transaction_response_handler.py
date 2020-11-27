"""Refused transaction response handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..manager import TransactionManager


class RefusedTransactionResponseHandler(BaseHandler):
    """Handler class for Refused transaction response."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle refused transaction response.

        Args:
            context: Request context
            responder: Responder callback
        """

        mgr = TransactionManager(context)
        await mgr.receive_refuse_response(context.message)
