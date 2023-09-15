"""Rotate ack handler."""

from .....messaging.base_handler import BaseHandler
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder

from ..messages.ack import RotateAck


class RotateAckHandler(BaseHandler):
    """Message handler class for rotate ack message."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle rotate ack message.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug("RotateAckHandler called with context %s", context)
        assert isinstance(context.message, RotateAck)
