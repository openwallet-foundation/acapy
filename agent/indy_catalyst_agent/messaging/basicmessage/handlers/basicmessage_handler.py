"""Basic message handler."""

from ...base_handler import BaseHandler, BaseResponder, RequestContext
from ..messages.basicmessage import BasicMessage


class BasicMessageHandler(BaseHandler):
    """Message handler class for basic messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for basic messages.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug(f"BasicMessageHandler called with context {context}")
        assert isinstance(context.message, BasicMessage)

        self._logger.info("Received basic message: %s", context.message.content)

        content = context.message.content
        if content.startswith("Reply with: "):
            reply = content[12:]
            reply = BasicMessage(content=reply, _l10n=context.message._l10n)
            await responder.send_reply(reply)
