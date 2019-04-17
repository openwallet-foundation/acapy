"""Handler for incoming forward invitation messages."""

from ...base_handler import BaseHandler, BaseResponder, HandlerError, RequestContext
from ..messages.forward_invitation import ForwardInvitation


class ForwardInvitationHandler(BaseHandler):
    """Handler for incoming forward invitation messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug("ForwardInvitationHandler called with context %s", context)
        assert isinstance(context.message, ForwardInvitation)

        if not context.connection_active:
            raise HandlerError(
                "No connection established for forward invitation message"
            )

        # Present the invitation to the user
