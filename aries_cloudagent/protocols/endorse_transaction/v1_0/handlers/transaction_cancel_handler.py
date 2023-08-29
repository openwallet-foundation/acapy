"""Cancel transaction request handler."""

from .....config.logging import get_adapted_logger_inst
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import TransactionManager, TransactionManagerError
from ..messages.cancel_transaction import CancelTransaction


class TransactionCancelHandler(BaseHandler):
    """Handler class for Cancel transaction request."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle cancel transaction request.

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
        self._logger.debug(f"TransactionCancelHandler called with context {context}")
        assert isinstance(context.message, CancelTransaction)

        if not context.connection_ready:
            raise HandlerException("No connection established")

        mgr = TransactionManager(context.profile)
        try:
            await mgr.receive_cancel_transaction(
                context.message, context.connection_record.connection_id
            )
        except TransactionManagerError:
            self._logger.exception("Error receiving cancel transaction request")
