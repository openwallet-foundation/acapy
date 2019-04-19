"""Handler for incoming route-update-response messages."""

from ...base_handler import BaseHandler, BaseResponder, HandlerException, RequestContext
from ..messages.route_update_response import RouteUpdateResponse


class RouteUpdateResponseHandler(BaseHandler):
    """Handler for incoming route-update-response messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, RouteUpdateResponse)

        if not context.connection_active or not context.sender_verkey:
            raise HandlerException("Cannot handle updated routes: no active connection")

        # TODO handle updated routes in connection manager
