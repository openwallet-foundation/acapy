"""Basic message handler."""

from ....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import CredentialManager
from ..messages.credential_issue import CredentialIssue


class CredentialIssueHandler(BaseHandler):
    """Message handler class for credential offers."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for credential offers.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug(f"CredentialHandler called with context {context}")
        assert isinstance(context.message, CredentialIssue)
        self._logger.info(f"Received credential: {context.message.issue}")

        if not context.connection_ready:
            raise HandlerException("No connection established for credential request")

        credential_manager = CredentialManager(context)

        credential_exchange_record = await credential_manager.receive_credential(
            context.message
        )

        # Automatically move to next state if flag is set
        if context.settings.get("debug.auto_store_credential"):
            (
                credential_exchange_record,
                credential_stored_message,
            ) = await credential_manager.store_credential(credential_exchange_record)

            # Notify issuer that credential was stored
            await responder.send_reply(credential_stored_message)
