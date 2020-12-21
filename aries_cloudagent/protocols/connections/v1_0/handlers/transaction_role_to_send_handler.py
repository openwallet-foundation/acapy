"""Transaction Role to send handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    RequestContext,
)

from ..manager import ConnectionManager, ConnectionManagerError
from ..messages.transaction_role_to_send import TransactionRoleToSend


class TransactionRoleToSendHandler(BaseHandler):
    """Handler class for sending transaction roles."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Handle transaction roles.

        Args:
            context: Request context
            responder: Responder callback
        """

        self._logger.debug(
            f"TransactionRoleToSendHandler called with context {context}"
        )
        assert isinstance(context.message, TransactionRoleToSend)

        session = await context.session()
        mgr = ConnectionManager(session)
        try:
            await mgr.set_transaction_their_role(
                context.message, context.message_receipt
            )
        except ConnectionManagerError:
            self._logger.exception("Error receiving transaction roles")
