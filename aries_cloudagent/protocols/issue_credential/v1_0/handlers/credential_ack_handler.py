"""Credential ack message handler."""

from .....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import CredentialManager
from ..messages.credential_ack import CredentialAck


class CredentialAckHandler(BaseHandler):
    """Message handler class for credential acks."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for credential acks.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug("CredentialAckHandler called with context %s", context)
        assert isinstance(context.message, CredentialAck)
        self._logger.info(
            "Received credential ack message: %s",
            context.message.serialize(as_string=True),
        )

        if not context.connection_ready:
            raise HandlerException("No connection established for credential ack")

        credential_manager = CredentialManager(context)

        await credential_manager.receive_credential_ack()
