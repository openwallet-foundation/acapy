"""Handler for incoming routes messages."""

from ...base_handler import BaseHandler, BaseResponder, HandlerError, RequestContext
from ..messages.routes import Routes


class RoutesHandler(BaseHandler):
    """Handler for incoming routes messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug("RoutesHandler called with context %s", context)
        assert isinstance(context.message, Routes)

        if not context.connection_active or not context.sender_verkey:
            raise HandlerError("Unknown sender for routes message")
        self._logger.info("Received routes from: %s", context.sender_verkey)

        # TODO: send admin message
