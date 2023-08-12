"""Handshake Reuse Message Handler under RFC 0434."""

import logging

from .....config.logging import get_logger_inst
from .....messaging.base_handler import BaseHandler
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder

from ..manager import OutOfBandManager, OutOfBandManagerError
from ..messages.reuse import HandshakeReuse


class HandshakeReuseMessageHandler(BaseHandler):
    """Handler class for Handshake Reuse Message Handler under RFC 0434."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle Handshake Reuse Message Handler under RFC 0434.

        Args:
            context: Request context
            responder: Responder callback
        """
        _logger: logging.Logger = get_logger_inst(
            profile=context.profile,
            logger_name=__name__,
        )
        _logger.debug(f"HandshakeReuseMessageHandler called with context {context}")
        assert isinstance(context.message, HandshakeReuse)

        profile = context.profile
        mgr = OutOfBandManager(profile)
        try:
            await mgr.receive_reuse_message(
                context.message, context.message_receipt, context.connection_record
            )
        except OutOfBandManagerError as e:
            _logger.exception(f"Error processing Handshake Reuse message, {e}")
