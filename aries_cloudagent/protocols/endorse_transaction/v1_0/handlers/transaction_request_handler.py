"""Transaction request handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..manager import TransactionManager


class TransactionRequestHandler(BaseHandler):
    """Handler class for transaction request."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle transaction request.

        Args:
            context: Request context
            responder: Responder callback
        """

        mgr = TransactionManager(context)
        await mgr.receive_request(context.message)
