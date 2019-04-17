"""Handler for incoming invitation request messages."""

from ...base_handler import BaseHandler, BaseResponder, HandlerError, RequestContext
from ..messages.invitation_request import InvitationRequest


class InvitationRequestHandler(BaseHandler):
    """Handler for incoming invitation request messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug("InvitationRequestHandler called with context %s", context)
        assert isinstance(context.message, InvitationRequest)

        if not context.connection_active:
            raise HandlerError(
                "No connection established for invitation request message"
            )

        # Prompt the user for acceptance
        # Create a new connection invitation and send it back in an Invitation message
