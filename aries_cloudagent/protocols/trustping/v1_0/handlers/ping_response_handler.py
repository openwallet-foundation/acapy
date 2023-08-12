"""Ping response handler."""

import logging

from .....config.logging import get_logger_inst
from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..messages.ping_response import PingResponse


class PingResponseHandler(BaseHandler):
    """Ping response handler class."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Handle ping response message.

        Args:
            context: Request context
            responder: Responder used to reply

        """
        _logger: logging.Logger = get_logger_inst(
            profile=context.profile,
            logger_name=__name__,
        )
        _logger.debug("PingResponseHandler called with context: %s", context)
        assert isinstance(context.message, PingResponse)

        _logger.info(
            "Received trust ping response from: %s", context.message_receipt.sender_did
        )

        if context.settings.get("debug.monitor_ping"):
            await context.profile.notify(
                "acapy::ping::response_received",
                {
                    "comment": context.message.comment,
                    "connection_id": context.message_receipt.connection_id,
                    "state": "response_received",
                    "thread_id": context.message._thread_id,
                },
            )

        # Nothing to do, Connection should be automatically promoted to 'active'
