"""Basic message handler."""

from ...base_handler import BaseHandler, BaseResponder, HandlerException, RequestContext

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

        await credential_manager.store_credential(context.message)
