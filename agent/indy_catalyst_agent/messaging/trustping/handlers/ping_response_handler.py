from ...base_handler import BaseHandler, BaseResponder, RequestContext
from ..messages.ping_response import PingResponse


class PingResponseHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        self._logger.debug("PingResponseHandler called with context: %s", context)
        assert isinstance(context.message, PingResponse)

        self._logger.info("Received trust ping response from: %s", context.sender_did)

        # Nothing to do, Connection should be automatically promoted to 'complete'
