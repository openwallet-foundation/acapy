from ...base_handler import BaseHandler, BaseResponder, RequestContext
from ..messages.connection_response import ConnectionResponse
from ....connection import ConnectionManager


class ConnectionResponseHandler(BaseHandler):

    async def handle(self, context: RequestContext, responder: BaseResponder):
        self._logger.debug(
            f"ConnectionResponseHandler called with context {context}"
        )
        assert isinstance(context.message, ConnectionResponse)

        mgr = ConnectionManager(context)
        target = await mgr.accept_response(context.message)
        # send trust ping?
