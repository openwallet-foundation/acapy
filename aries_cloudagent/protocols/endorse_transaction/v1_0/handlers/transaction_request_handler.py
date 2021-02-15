"""Transaction request handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
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

        if not context.connection_ready:
            raise HandlerException("No connection established")

        profile_session = await context.session()
        mgr = TransactionManager(profile_session)
        try:
            await mgr.receive_request(
                context.message, context.connection_record.connection_id
            )
        except TransactionManagerError:
            self._logger.exception("Error receiving transaction request")
