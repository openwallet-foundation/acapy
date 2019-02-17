from ...base_handler import BaseHandler, BaseResponder, RequestContext
from ..messages.connection_invitation import ConnectionInvitation
from ..manager import ConnectionManager, ConnectionRecord


class ConnectionInvitationHandler(BaseHandler):
    """Handler for connection invitations."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        self._logger.debug(f"ConnectionInvitationHandler called with context {context}")
        assert isinstance(context.message, ConnectionInvitation)

        # Prevent invitation from being submitted by normal means (POST/websocket)
        # if context.transport_type != "invitation":
        #    raise ConnectionError(
        #       "Invitation must be submitted as part of a GET request"
        #    )

        role = None
        if context.transport_type == "router_invitation":
            role = ConnectionRecord.ROLE_ROUTER

        mgr = ConnectionManager(context)
        request, target = await mgr.accept_invitation(context.message, their_role=role)
        await responder.send_outbound(request, target)
