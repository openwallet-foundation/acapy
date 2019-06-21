"""Ping response handler."""

from ...base_handler import BaseHandler, BaseResponder, RequestContext
from ...connections.manager import ConnectionManager

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

        self._logger.info(
            "Received trust ping response from: %s", context.message_delivery.sender_did
        )

        # Nothing to do, Connection should be automatically promoted to 'active'

        conn_mgr = ConnectionManager(context)
        await conn_mgr.log_activity(
            context.connection_record,
            "ping",
            context.connection_record.DIRECTION_RECEIVED,
        )
