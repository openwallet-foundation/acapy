"""Keylist update request handler."""


from ....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext
)

from ..messages.keylist_update_request import KeylistUpdateRequest
from ..manager import RouteCoordinationManager


class KeylistUpdateRequestHandler(BaseHandler):
    """Handler for keylist update request."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for keylist update request.

        Args:
            context: request context
            responder: responder callback

        """
        self._logger.debug(
            "KeylistUpdateRequestHandler called with context %s",
            context
        )
        assert isinstance(context.message, KeylistUpdateRequest)
        self._logger.info(
            "Received keylist update request message: %s",
            context.message.serialize(as_string=True)
        )

        if not context.connection_ready:
            raise HandlerException("No connection found for keylist update request")

        routing_manager = RouteCoordinationManager(context)

        await routing_manager.receive_keylist_update_request()
