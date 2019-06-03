"""Connection response handler."""

from ...base_handler import BaseHandler, BaseResponder, RequestContext
from ..messages.connection_response import ConnectionResponse
from ..manager import ConnectionManager
from ...trustping.messages.ping import Ping


class ConnectionResponseHandler(BaseHandler):
    """Handler class for connection responses."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle connection response.

        Args:
            context: Request context
            responder: Responder callback
        """
        self._logger.debug(f"ConnectionResponseHandler called with context {context}")
        assert isinstance(context.message, ConnectionResponse)

        mgr = ConnectionManager(context)
        connection = await mgr.accept_response(
            context.message, context.message_delivery
        )

        # send trust ping in response
        await responder.send(Ping(), connection_id=connection.connection_id)
