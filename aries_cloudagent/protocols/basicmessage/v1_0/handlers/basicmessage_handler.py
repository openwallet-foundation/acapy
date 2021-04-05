"""Basic message handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

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
        self._logger.debug("BasicMessageHandler called with context %s", context)
        assert isinstance(context.message, BasicMessage)

        self._logger.info("Received basic message: %s", context.message.content)

        body = context.message.content
        meta = {"content": body}

        # For Workshop: mark invitations as copyable
        if context.message.content and context.message.content.startswith(
            ("http:", "https:")
        ):
            meta["copy_invite"] = True

        payload = {
            "connection_id": context.connection_record.connection_id,
            "message_id": context.message._id,
            "content": body,
            "state": "received",
            "sent_time": context.message.sent_time,
        }

        if "l10n" in context.message._decorators:
            payload["locale"] = context.message._decorators["l10n"].locale

        await context.profile.notify("acapy::basicmessage::received", payload)

        reply = None
        if body:
            if context.settings.get("debug.auto_respond_messages"):
                if "received your message" not in body:
                    reply = f"{context.default_label} received your message"
            elif body.startswith("Reply with: "):
                reply = body[12:]

        if reply:
            reply_msg = BasicMessage(content=reply)
            reply_msg.assign_thread_from(context.message)
            reply_msg.assign_trace_from(context.message)
            if "l10n" in context.message._decorators:
                reply_msg._decorators["l10n"] = context.message._decorators["l10n"]
            await responder.send_reply(reply_msg)
