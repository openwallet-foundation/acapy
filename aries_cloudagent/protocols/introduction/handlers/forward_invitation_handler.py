"""Handler for incoming forward invitation messages."""

from ....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ...connections.manager import ConnectionManager

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
        connection_mgr = ConnectionManager(context)
        connection = await connection_mgr.receive_invitation(
            context.message.invitation, their_role=None
        )

        # Auto-accept
        if context.settings.get("accept_invites"):
            request = await connection_mgr.create_request(connection)
            await responder.send(request, connection_id=connection.connection_id)
