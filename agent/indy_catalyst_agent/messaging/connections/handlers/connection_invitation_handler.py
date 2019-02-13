from ...base_handler import BaseHandler, BaseResponder, RequestContext
from ..messages.connection_invitation import ConnectionInvitation
from ....connection import ConnectionManager, ConnectionError


class ConnectionInvitationHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        self._logger.debug(f"ConnectionInvitationHandler called with context {context}")
        assert isinstance(context.message, ConnectionInvitation)

        # Prevent invitation from being submitted by normal means (POST/websocket)
        # if context.transport_type != "invitation":
        #    raise ConnectionError("Invitation must be submitted as part of a GET request")

        mgr = ConnectionManager(context)
        request, target = await mgr.accept_invitation(context.message)
        await responder.send_outbound(request, target)
