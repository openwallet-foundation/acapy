"""Handler for incoming forward invitation messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from .....protocols.connections.v1_0.manager import ConnectionManager

from ..messages.forward_invitation import ForwardInvitation


class ForwardInvitationHandler(BaseHandler):
    """Handler for incoming forward invitation messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug("ForwardInvitationHandler called with context %s", context)
        assert isinstance(context.message, ForwardInvitation)

        if not context.connection_ready:
            raise HandlerException(
                "No connection established for forward invitation message"
            )

        # Store invitation
        session = await context.session()
        connection_mgr = ConnectionManager(session)
        connection = await connection_mgr.receive_invitation(context.message.invitation)

        # Auto-accept
        if context.settings.get("accept_invites"):
            request = await connection_mgr.create_request(connection)
            await responder.send(request, connection_id=connection.connection_id)
