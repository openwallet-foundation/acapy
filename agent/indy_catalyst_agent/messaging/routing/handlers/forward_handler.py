"""Handler for incoming forward messages."""

from ...base_handler import BaseHandler, BaseResponder, HandlerError, RequestContext
from ..messages.forward import Forward
from ....connection import ConnectionManager, ConnectionManagerError
from ..manager import RoutingManager, RoutingManagerError


class ForwardHandler(BaseHandler):
    """Handler for incoming forward messages."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation."""
        self._logger.debug("ForwardHandler called with context %s", context)
        assert isinstance(context.message, Forward)

        if not context.message_delivery.recipient_verkey:
            raise HandlerError("Cannot forward message: unknown recipient")
        self._logger.info(
            "Received forward for: %s", context.message_delivery.recipient_verkey
        )

        packed = context.message.msg.encode("ascii")
        rt_mgr = RoutingManager(context)
        targets = [context.message.to]
        for target in targets:
            try:
                recipient = await rt_mgr.get_recipient(target)
            except RoutingManagerError:
                self._logger.exception("Error resolving recipient")
                continue

            conn_mgr = ConnectionManager(context)
            try:
                conn = await conn_mgr.find_connection(None, None, recipient)
            except ConnectionManagerError:
                self._logger.exception("Error resolving connection for route")

            await self.responder.send(packed, connection_id=conn.connection_id)
