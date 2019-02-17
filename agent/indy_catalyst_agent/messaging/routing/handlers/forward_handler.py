from ...base_handler import BaseHandler, BaseResponder, HandlerError, RequestContext
from ..messages.forward import Forward
from ....connection import ConnectionManager, ConnectionManagerError
from ..manager import RoutingManager, RoutingManagerError
from ....wallet.util import b64_to_bytes


class ForwardHandler(BaseHandler):
    """Handler for incoming forward messages"""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """Message handler implementation"""
        self._logger.debug("ForwardHandler called with context %s", context)
        assert isinstance(context.message, Forward)

        if not context.recipient_verkey:
            raise HandlerError("Cannot forward message: unknown recipient")
        self._logger.info("Received forward for: %s", context.recipient_verkey)

        packed = b64_to_bytes(context.message.msg)
        rt_mgr = RoutingManager(context)
        for target in context.message.to:
            try:
                recipient = await rt_mgr.get_recipient(target)
            except RoutingManagerError:
                self._logger.exception("Error resolving recipient")
                continue

            conn_mgr = ConnectionManager(context)
            try:
                conn = await conn_mgr.find_connection(recipient)
            except ConnectionManagerError:
                self._logger.exception("Error resolving connection for route")

            await self.responder.send_outbound(packed, conn.target)
