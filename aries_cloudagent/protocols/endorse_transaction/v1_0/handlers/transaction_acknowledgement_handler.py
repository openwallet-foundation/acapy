"""Transaction acknowledgement message handler."""

import logging

from .....config.logging import get_logger_inst
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
        _logger: logging.Logger = get_logger_inst(
            profile=context.profile,
            logger_name=__name__,
        )
        _logger.debug(
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
            _logger.exception("Error receiving transaction acknowledgement")
