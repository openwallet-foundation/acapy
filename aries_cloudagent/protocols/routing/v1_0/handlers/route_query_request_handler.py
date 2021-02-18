"""Handler for incoming route-query-request messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import RoutingManager
from ..messages.route_query_request import RouteQueryRequest
from ..messages.route_query_response import RouteQueryResponse


class RouteQueryRequestHandler(BaseHandler):
    """Handler for incoming route-query-request messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, RouteQueryRequest)

        if not context.connection_ready:
            raise HandlerException("Cannot query routes: no active connection")

        mgr = RoutingManager(context.profile)
        result = await mgr.get_routes(
            context.connection_record.connection_id, context.message.filter
        )
        response = RouteQueryResponse(routes=result)
        await responder.send_reply(response)
