"""Rotate hangup handler."""

from .....messaging.base_handler import BaseHandler
from .....messaging.request_context import RequestContext
from .....messaging.responder import BaseResponder
from ..manager import DIDRotateManager
from ..messages.hangup import Hangup


class HangupHandler(BaseHandler):
    """Message handler class for rotate message."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle rotate hangup message.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug("HangupHandler called with context %s", context)
        assert isinstance(context.message, Hangup)

        connection_record = context.connection_record

        profile = context.profile
        did_rotate_mgr = DIDRotateManager(profile)

        await did_rotate_mgr.receive_hangup(connection_record)
