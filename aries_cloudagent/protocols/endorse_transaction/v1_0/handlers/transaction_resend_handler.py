"""Transaction resend handler."""

from .....config.logging import get_adapted_logger_inst
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import TransactionManager, TransactionManagerError
from ..messages.transaction_resend import TransactionResend


class TransactionResendHandler(BaseHandler):
    """Handler class for transaction resend."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle transaction resend.

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
        self._logger.debug(f"TransactionResendHandler called with context {context}")
        assert isinstance(context.message, TransactionResend)

        if not context.connection_ready:
            raise HandlerException("No connection established")

        mgr = TransactionManager(context.profile)
        try:
            await mgr.receive_transaction_resend(
                context.message, context.connection_record.connection_id
            )
        except TransactionManagerError:
            self._logger.exception("Error receiving resend transaction request")
