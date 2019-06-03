"""Connect invitation handler."""

from ...base_handler import BaseHandler, BaseResponder, RequestContext
from ..messages.connection_invitation import ConnectionInvitation
from ..manager import ConnectionManager, ConnectionRecord


class ConnectionInvitationHandler(BaseHandler):
    """Handler class for connection invitations."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle connection invitation.

        Args:
            context: Request context
            responder: Responder callback
        """

        self._logger.debug(f"ConnectionInvitationHandler called with context {context}")
        assert isinstance(context.message, ConnectionInvitation)

        # Prevent invitation from being submitted by normal means (POST/websocket)
        # if context.message_delivery.transport_type != "invitation":
        #    raise ConnectionError(
        #       "Invitation must be submitted as part of a GET request"
        #    )

        role = None
        if context.message_delivery.transport_type == "router_invitation":
            role = ConnectionRecord.ROLE_ROUTER

        mgr = ConnectionManager(context)
        conn = await mgr.receive_invitation(context.message, their_role=role)

        if conn.requires_routing:
            await mgr.update_routing(conn)
        else:
            request = await mgr.create_request(conn)
            target = await mgr.get_connection_target(conn)
            await responder.send(request, target=target)
