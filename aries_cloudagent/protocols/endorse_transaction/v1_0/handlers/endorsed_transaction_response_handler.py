"""Endorsed transaction response handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from .....storage.error import StorageError

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

        # profile_session = await context.session()
        mgr = TransactionManager(context.profile)
        try:
            transaction = await mgr.receive_endorse_response(context.message)
        except TransactionManagerError:
            self._logger.exception("Error receiving endorsed transaction response")

        # Automatically write transaction if flag is set
        if context.settings.get("endorser.auto_write"):
            try:
                (
                    transaction,
                    transaction_acknowledgement_message,
                ) = await mgr.complete_transaction(transaction, False)

                await responder.send_reply(
                    transaction_acknowledgement_message,
                    connection_id=transaction.connection_id,
                )
            except (StorageError, TransactionManagerError) as err:
                self._logger.exception(err)
