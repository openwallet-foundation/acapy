"""Handler for incoming invitation request messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)
from .....protocols.connections.v1_0.manager import ConnectionManager
from ..messages.invitation_request import InvitationRequest
from ..messages.invitation import Invitation


class InvitationRequestHandler(BaseHandler):
    """Handler for incoming invitation request messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug("InvitationRequestHandler called with context %s", context)
        assert isinstance(context.message, InvitationRequest)

        if not context.connection_ready:
            raise HandlerException(
                "No connection established for invitation request message"
            )

        # Need a way to prompt the user for acceptance?

        if context.settings.get("accept_requests"):
            # Create a new connection invitation and send it back in an Invitation
            session = await context.session()
            connection_mgr = ConnectionManager(session)
            _connection, invite = await connection_mgr.create_invitation()
            response = Invitation(invitation=invite)
            response.assign_thread_from(context.message)
            response.assign_trace_from(context.message)
            await responder.send_reply(response)
