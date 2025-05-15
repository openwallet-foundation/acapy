"""Handshake Reuse Message Handler under RFC 0434."""

from .....messaging.base_handler import BaseHandler, HandlerException
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
        self._logger.debug("HandshakeReuseMessageHandler called with context %s", context)
        assert isinstance(context.message, HandshakeReuse)

        if not context.connection_ready:
            raise HandlerException("No connection established")

        profile = context.profile
        mgr = OutOfBandManager(profile)
        try:
            await mgr.receive_reuse_message(
                context.message, context.message_receipt, context.connection_record
            )
        except OutOfBandManagerError as e:
            self._logger.exception(f"Error processing Handshake Reuse message, {e}")
