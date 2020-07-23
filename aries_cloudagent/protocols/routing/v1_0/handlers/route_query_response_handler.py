"""Handler for incoming route-query-response messages."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..messages.route_query_response import RouteQueryResponse


class RouteQueryResponseHandler(BaseHandler):
    """Handler for incoming route-query-response messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug(
            "%s called with context %s", self.__class__.__name__, context
        )
        assert isinstance(context.message, RouteQueryResponse)

        if not context.connection_ready:
            raise HandlerException(
                "Cannot handle route query response: no active connection"
            )

        # TODO handle response in connection manager
