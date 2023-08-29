"""Transaction acknowledgement message handler."""

from .....config.logging import get_adapted_logger_inst
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import TransactionManager, TransactionManagerError
from ..messages.transaction_acknowledgement import TransactionAcknowledgement


class TransactionAcknowledgementHandler(BaseHandler):
    """Message handler class for Acknowledging transaction."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle transaction acknowledgement message.

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
            f"TransactionAcknowledgementHandler called with context {context}"
        )
        assert isinstance(context.message, TransactionAcknowledgement)

        if not context.connection_ready:
            raise HandlerException("No connection established")

        mgr = TransactionManager(context.profile)
        try:
            await mgr.receive_transaction_acknowledgement(
                context.message, context.connection_record.connection_id
            )
        except TransactionManagerError:
            self._logger.exception("Error receiving transaction acknowledgement")
