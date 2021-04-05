"""Endorsed transaction response handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import TransactionManager, TransactionManagerError
from ..messages.endorsed_transaction_response import EndorsedTransactionResponse


class EndorsedTransactionResponseHandler(BaseHandler):
    """Handler class for Endorsed transaction response."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle endorsed transaction response.

        Args:
            context: Request context
            responder: Responder callback
        """

        self._logger.debug(
            f"EndorsedTransactionResponseHandler called with context {context}"
        )
        assert isinstance(context.message, EndorsedTransactionResponse)

        if not context.connection_ready:
            raise HandlerException("No connection established")

        profile_session = await context.session()
        mgr = TransactionManager(profile_session)
        try:
            await mgr.receive_endorse_response(context.message)
        except TransactionManagerError:
            self._logger.exception("Error receiving endorsed transaction response")
