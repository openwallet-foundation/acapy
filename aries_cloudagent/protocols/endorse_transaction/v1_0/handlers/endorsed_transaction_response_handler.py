"""Endorsed transaction response handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..manager import TransactionManager


class EndorsedTransactionResponseHandler(BaseHandler):
    """Handler class for Endorsed transaction response."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle endorsed transaction response.

        Args:
            context: Request context
            responder: Responder callback
        """

        mgr = TransactionManager(context)
        await mgr.receive_endorse_response(context.message)
