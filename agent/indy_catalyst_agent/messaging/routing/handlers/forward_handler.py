from ...base_handler import BaseHandler, BaseResponder, HandlerError, RequestContext
from ..messages.forward import Forward


class ForwardHandler(BaseHandler):
    """Handler for incoming forward messages"""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation"""
        self._logger.debug("ForwardHandler called with context %s", context)
        assert isinstance(context.message, Forward)

        if not context.recipient_verkey:
            raise HandlerError("Cannot forward message: unknown recipient")
        self._logger.info("Received forward for: %s", context.recipient_verkey)
