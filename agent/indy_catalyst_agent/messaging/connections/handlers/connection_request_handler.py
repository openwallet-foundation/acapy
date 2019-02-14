from ...base_handler import BaseHandler, BaseResponder, RequestContext
from ..messages.connection_request import ConnectionRequest
from ....connection import ConnectionManager


class ConnectionRequestHandler(BaseHandler):
    """ """
    async def handle(self, context: RequestContext, responder: BaseResponder):
        self._logger.debug(f"ConnectionRequestHandler called with context {context}")
        assert isinstance(context.message, ConnectionRequest)

        mgr = ConnectionManager(context)
        response, target = await mgr.accept_request(context.message)

        self._logger.debug("Sending connection response to target: %s", target)
        await responder.send_outbound(response, target)
