from ...base_handler import BaseHandler, BaseResponder, HandlerError, RequestContext
from ..manager import RoutingManager
from ..messages.delete_routes import DeleteRoutes


class DeleteRoutesHandler(BaseHandler):
    """Handler for incoming delete_routes messages"""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation"""
        self._logger.debug("DeleteRoutesHandler called with context %s", context)
        assert isinstance(context.message, DeleteRoutes)

        if not context.connection_active or not context.sender_verkey:
            raise HandlerError("Cannot delete routes: no connection")
        self._logger.info("Received delete routes from: %s", context.sender_verkey)

        mgr = RoutingManager(context)
        await mgr.delete_routes(context.message.recipient_keys)
