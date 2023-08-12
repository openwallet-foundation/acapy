"""Transaction Job to send handler."""

import logging

from .....config.logging import get_logger_inst
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
        _logger: logging.Logger = get_logger_inst(
            profile=context.profile,
            logger_name=__name__,
        )
        _logger.debug(f"TransactionJobToSendHandler called with context {context}")
        assert isinstance(context.message, TransactionJobToSend)

        mgr = TransactionManager(context.profile)
        try:
            await mgr.set_transaction_their_job(
                context.message, context.message_receipt
            )
        except TransactionManagerError:
            _logger.exception("Error receiving transaction jobs")
