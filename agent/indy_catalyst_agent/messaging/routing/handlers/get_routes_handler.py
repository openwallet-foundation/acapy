"""Handler for incoming GetRoutes messages."""

from ...base_handler import BaseHandler, BaseResponder, HandlerError, RequestContext
from ..manager import RoutingManager
from ..messages.get_routes import GetRoutes
from ..messages.routes import Routes


class GetRoutesHandler(BaseHandler):
    """Handler for incoming GetRoutes messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug("GetRoutesHandler called with context %s", context)
        assert isinstance(context.message, GetRoutes)

        if not context.connection_active or not context.sender_verkey:
            raise HandlerError("Cannot get routes: no connection")
        self._logger.info("Received get routes from: %s", context.sender_verkey)

        mgr = RoutingManager(context)
        result = await mgr.get_routes()
        await responder.send_reply(Routes(recipient_keys=result))
