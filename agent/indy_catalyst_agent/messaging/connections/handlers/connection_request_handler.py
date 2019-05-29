"""Connection request handler."""

from ...base_handler import BaseHandler, BaseResponder, RequestContext
from ..messages.connection_request import ConnectionRequest
from ..manager import ConnectionManager


class ConnectionRequestHandler(BaseHandler):
    """Handler class for connection requests."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle connection request.

        Args:
            context: Request context
            responder: Responder callback
        """

        self._logger.debug(f"ConnectionRequestHandler called with context {context}")
        assert isinstance(context.message, ConnectionRequest)

        mgr = ConnectionManager(context)
        connection = await mgr.receive_request(
            context.message, context.message_delivery
        )

        if context.settings.get("accept_requests"):
            response = await mgr.create_response(connection)
            target = await mgr.get_connection_target(connection)

            self._logger.debug("Sending connection response to target: %s", target)
            await responder.send(response, target=target)
