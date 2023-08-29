"""Transaction Job to send handler."""

from .....config.logging import get_adapted_logger_inst
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..manager import TransactionManager, TransactionManagerError
from ..messages.transaction_job_to_send import TransactionJobToSend


class TransactionJobToSendHandler(BaseHandler):
    """Handler class for sending transaction jobs."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle transaction jobs.

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
        self._logger.debug(f"TransactionJobToSendHandler called with context {context}")
        assert isinstance(context.message, TransactionJobToSend)

        mgr = TransactionManager(context.profile)
        try:
            await mgr.set_transaction_their_job(
                context.message, context.message_receipt
            )
        except TransactionManagerError:
            self._logger.exception("Error receiving transaction jobs")
