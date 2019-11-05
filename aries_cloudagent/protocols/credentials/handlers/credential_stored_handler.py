"""Credential stored message handler."""

from ....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import CredentialManager
from ..messages.credential_stored import CredentialStored


class CredentialStoredHandler(BaseHandler):
    """Message handler class for credential offers."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for credential stored messages.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug(f"CredentialStoredHandler called with context {context}")
        assert isinstance(context.message, CredentialStored)
        self._logger.info(f"Received credential stored message: {context.message}")

        if not context.connection_ready:
            raise HandlerException("No connection established for credential_exchange")

        credential_manager = CredentialManager(context)

        await credential_manager.credential_stored(context.message)
