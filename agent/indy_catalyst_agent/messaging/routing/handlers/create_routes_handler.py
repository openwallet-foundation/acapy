"""Handler for incoming create_routes messages."""

from ...base_handler import BaseHandler, BaseResponder, HandlerError, RequestContext
from ..manager import RoutingManager
from ..messages.create_routes import CreateRoutes
from ..messages.routes import Routes


class CreateRoutesHandler(BaseHandler):
    """Handler for incoming create_routes messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug("CreateRoutesHandler called with context %s", context)
        assert isinstance(context.message, CreateRoutes)

        if not context.connection_active or not context.sender_verkey:
            raise HandlerError("Cannot create routes: no connection")
        self._logger.info("Received create routes from: %s", context.sender_verkey)

        mgr = RoutingManager(context)
        await mgr.create_routes(context.message.recipient_keys)

        result = await mgr.get_routes()
        await responder.send_reply(Routes(recipient_keys=result))
