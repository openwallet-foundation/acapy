from ...base_handler import BaseHandler, BaseResponder, RequestContext
from ..messages.basicmessage import BasicMessage

class BasicMessageHandler(BaseHandler):
    async def handle(self, context: RequestContext, responder: BaseResponder):
        self._logger.debug(
            f"BasicMessageHandler called with context {context}"
        )
        assert isinstance(context.message, BasicMessage)

        self._logger.info("Received basic message: %s", context.message.content)
