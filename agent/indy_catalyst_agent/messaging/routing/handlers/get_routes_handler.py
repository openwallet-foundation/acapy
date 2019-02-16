from ...base_handler import BaseHandler, BaseResponder, HandlerError, RequestContext
from ..messages.get_routes import GetRoutes


class GetRoutesHandler(BaseHandler):
    """Handler for incoming create_routes messages"""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation"""
        self._logger.debug("GetRoutesHandler called with context %s", context)
        assert isinstance(context.message, GetRoutes)

        if not context.connection_active or not context.sender_verkey:
            raise HandlerError("Cannot get routes: no connection")
        self._logger.info("Received get routes from: %s", context.sender_verkey)

        # mgr = RoutesManager(context)
        # result = await mgr.get_routes()
