"""Handler for incoming invitation messages."""

from ...base_handler import BaseHandler, BaseResponder, HandlerError, RequestContext
from ..messages.invitation import Invitation


class InvitationHandler(BaseHandler):
    """Handler for incoming invitation messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug("InvitationHandler called with context %s", context)
        assert isinstance(context.message, Invitation)

        if not context.connection_active:
            raise HandlerError("No connection established for invitation message")

        # Look up existing invitation request by thread
        # Create an invitation forward message and send to the responder
