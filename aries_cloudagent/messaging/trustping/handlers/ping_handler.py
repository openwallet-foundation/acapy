"""Ping handler."""

from ...base_handler import BaseHandler, BaseResponder, RequestContext
from ...connections.manager import ConnectionManager
from ..messages.ping import Ping
from ..messages.ping_response import PingResponse


class PingHandler(BaseHandler):
    """Ping handler class."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle ping message.

        Args:
            context: Request context
            responder: Responder used to reply

        """
        self._logger.debug(f"PingHandler called with context {context}")
        assert isinstance(context.message, Ping)

        self._logger.info(
            "Received trust ping from: %s", context.message_delivery.sender_did
        )

        if not context.connection_ready:
            self._logger.info(
                "Connection not active, skipping ping response: %s",
                context.message_delivery.sender_did,
            )
            return

        conn_mgr = ConnectionManager(context)
        await conn_mgr.log_activity(
            context.connection_record,
            "ping",
            context.connection_record.DIRECTION_RECEIVED,
        )

        if context.message.response_requested:
            reply = PingResponse()
            reply.assign_thread_from(context.message)
            await responder.send_reply(reply)
            await conn_mgr.log_activity(
                context.connection_record,
                "ping",
                context.connection_record.DIRECTION_SENT,
            )
