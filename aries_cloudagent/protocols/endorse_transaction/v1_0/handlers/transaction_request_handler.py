"""Transaction request handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..manager import TransactionManager, TransactionManagerError
from ..messages.transaction_request import TransactionRequest


class TransactionRequestHandler(BaseHandler):
    """Handler class for transaction request."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle transaction request.

        Args:
            context: Request context
            responder: Responder callback
        """

        self._logger.debug(f"TransactionRequestHandler called with context {context}")
        assert isinstance(context.message, TransactionRequest)

        mgr = TransactionManager(context, context.profile)
        try:
            await mgr.receive_request(context.message)
        except TransactionManagerError:
            self._logger.exception("Error receiving transaction request")
