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

        meta = {"content": context.message.content}

        # For Workshop: mark invitations as copyable
        if context.message.content and context.message.content.startswith("http"):
            meta["copy_invite"] = True

        await context.connection_record.log_activity(
            context, "message", context.connection_record.DIRECTION_RECEIVED, meta
        )

        body = context.message.content
        reply = None
        if context.settings.get("debug.auto_respond_messages"):
            if (
                "received your message" not in body
                and "received your invitation" not in body
            ):
                if context.message.content.startswith("http"):
                    reply = f"{context.default_label} received your invitation"
                else:
                    reply = f"{context.default_label} received your message"
        elif body.startswith("Reply with: "):
            reply = body[12:]

        if reply:
            reply_msg = BasicMessage(content=reply, _l10n=context.message._l10n)
            await responder.send_reply(reply_msg)
            await context.connection_record.log_activity(
                context,
                "message",
                context.connection_record.DIRECTION_SENT,
                {"content": reply},
            )
