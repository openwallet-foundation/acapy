"""Rotate ack handler."""

from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from ..manager import DIDRotateManager
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

        if not context.connection_ready:
            raise HandlerException("No connection established")

        connection_record = context.connection_record
        ack = context.message

        profile = context.profile
        did_rotate_mgr = DIDRotateManager(profile)

        await did_rotate_mgr.receive_ack(connection_record, ack)
