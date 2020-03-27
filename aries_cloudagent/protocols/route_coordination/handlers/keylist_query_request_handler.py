"""Keylist query request handler."""


from ....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext
)

from ..messages.keylist_query import KeylistQuery
from ..manager import RouteCoordinationManager


class KeylistQueryRequestHandler(BaseHandler):
    """Handler for keylist query request."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for keylist query request.

        Args:
            context: request context
            responder: responder callback

        """
        self._logger.debug(
            "KeylistUpdateRequestHandler called with context %s",
            context
        )
        assert isinstance(context.message, KeylistQuery)
        self._logger.info(
            "Received keylist update request message: %s",
            context.message.serialize(as_string=True)
        )

        if not context.connection_ready:
            raise HandlerException("No connection found for keylist update request")

        routing_manager = RouteCoordinationManager(context)

        await routing_manager.receive_keylist_query_request()
