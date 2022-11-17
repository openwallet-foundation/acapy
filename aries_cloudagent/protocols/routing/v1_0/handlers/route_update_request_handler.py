"""Handler for incoming route-update-request messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import RoutingManager
from ..messages.route_update_request import RouteUpdateRequest
from ..messages.route_update_response import RouteUpdateResponse


class RouteUpdateRequestHandler(BaseHandler):
    """Handler for incoming route-update-request messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, RouteUpdateRequest)

        if not context.connection_ready:
            raise HandlerException("Cannot update routes: no active connection")

        mgr = RoutingManager(context.profile)
        updated = await mgr.update_routes(
            context.connection_record.connection_id, context.message.updates
        )
        response = RouteUpdateResponse(updated=updated)
        await responder.send_reply(response)
