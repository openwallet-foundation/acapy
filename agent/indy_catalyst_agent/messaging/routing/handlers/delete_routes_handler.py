"""Handler for incoming delete_routes messages."""

from ...base_handler import BaseHandler, BaseResponder, HandlerError, RequestContext
from ..manager import RoutingManager
from ..messages.delete_routes import DeleteRoutes
from ..messages.routes import Routes


class DeleteRoutesHandler(BaseHandler):
    """Handler for incoming delete_routes messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug("DeleteRoutesHandler called with context %s", context)
        assert isinstance(context.message, DeleteRoutes)

        if not context.connection_active or not context.message_delivery.sender_verkey:
            raise HandlerError("Cannot delete routes: no connection")
        self._logger.info(
            "Received delete routes from: %s", context.message_delivery.sender_verkey
        )

        mgr = RoutingManager(context)
        await mgr.delete_routes(context.message.recipient_keys)

        result = await mgr.get_routes()
        await responder.send_reply(Routes(recipient_keys=result))
