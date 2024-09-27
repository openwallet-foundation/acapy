"""Rotate handler."""

from .....messaging.base_handler import BaseHandler, HandlerException
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from ..manager import DIDRotateManager
from ..messages.rotate import Rotate


class RotateHandler(BaseHandler):
    """Message handler class for rotate message."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle rotate message.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug("RotateHandler called with context %s", context)
        assert isinstance(context.message, Rotate)

        if not context.connection_ready:
            raise HandlerException("No connection established")

        connection_record = context.connection_record
        rotate = context.message

        profile = context.profile
        did_rotate_mgr = DIDRotateManager(profile)

        if record := await did_rotate_mgr.receive_rotate(connection_record, rotate):
            await did_rotate_mgr.commit_rotate(connection_record, record)
