"""Transaction request handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from .....storage.error import StorageError

from ..manager import TransactionManager, TransactionManagerError
from ..messages.transaction_request import TransactionRequest
from ..models.transaction_record import TransactionRecord


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

        mgr = TransactionManager(context.profile)
        try:
            transaction = await mgr.receive_request(
                context.message, context.connection_record.connection_id
            )
        except TransactionManagerError as err:
            self._logger.exception(err)
            return

        # Automatically endorse transaction if flag is set
        if context.settings.get("endorser.auto_endorse"):
            try:
                (
                    transaction,
                    endorsed_transaction_response,
                ) = await mgr.create_endorse_response(
                    transaction=transaction,
                    state=TransactionRecord.STATE_TRANSACTION_ENDORSED,
                )

                await responder.send_reply(
                    endorsed_transaction_response,
                    connection_id=transaction.connection_id,
                )
            except (StorageError, TransactionManagerError) as err:
                self._logger.exception(err)
