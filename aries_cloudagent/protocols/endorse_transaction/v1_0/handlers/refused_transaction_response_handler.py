"""Refused transaction response handler."""

from .....config.logging import get_adapted_logger_inst
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import TransactionManager, TransactionManagerError
from ..messages.refused_transaction_response import RefusedTransactionResponse


class RefusedTransactionResponseHandler(BaseHandler):
    """Handler class for Refused transaction response."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle refused transaction response.

        Args:
            context: Request context
            responder: Responder callback
        """
        profile = context.profile
        self._logger = get_adapted_logger_inst(
            logger=self._logger,
            log_file=profile.settings.get("log.file"),
            wallet_id=profile.settings.get("wallet.id"),
        )
        self._logger.debug(
            f"RefusedTransactionResponseHandler called with context {context}"
        )
        assert isinstance(context.message, RefusedTransactionResponse)

        if not context.connection_ready:
            raise HandlerException("No connection established")

        mgr = TransactionManager(context.profile)
        try:
            await mgr.receive_refuse_response(context.message)
        except TransactionManagerError:
            self._logger.exception("Error receiving refused transaction response")
