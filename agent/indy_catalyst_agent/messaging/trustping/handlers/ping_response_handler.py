"""Ping response handler."""

from ...base_handler import BaseHandler, BaseResponder, RequestContext
from ..messages.ping_response import PingResponse


class PingResponseHandler(BaseHandler):
    """Ping response handler class."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle ping response message.

        Args:
            context: Request context
            responder: Responder used to reply

        """

        self._logger.debug("PingResponseHandler called with context: %s", context)
        assert isinstance(context.message, PingResponse)

        self._logger.info("Received trust ping response from: %s", context.sender_did)

        # Nothing to do, Connection should be automatically promoted to 'active'

        await context.connection_record.log_activity(
            context.storage,
            context.service_factory,
            "ping",
            context.connection_record.DIRECTION_RECEIVED,
        )
