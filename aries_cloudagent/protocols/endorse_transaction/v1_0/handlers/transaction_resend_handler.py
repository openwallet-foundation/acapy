"""Transaction resend handler."""

import logging

from .....config.logging import get_logger_inst
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
        _logger: logging.Logger = get_logger_inst(
            profile=context.profile,
            logger_name=__name__,
        )
        _logger.debug(f"TransactionResendHandler called with context {context}")
        assert isinstance(context.message, TransactionResend)

        if not context.connection_ready:
            raise HandlerException("No connection established")

        mgr = TransactionManager(context.profile)
        try:
            await mgr.receive_transaction_resend(
                context.message, context.connection_record.connection_id
            )
        except TransactionManagerError:
            _logger.exception("Error receiving resend transaction request")
