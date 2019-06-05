"""Credential request handler."""

from ...base_handler import BaseHandler, BaseResponder, HandlerException, RequestContext

from ..manager import CredentialManager
from ..messages.credential_request import CredentialRequest
from ....cache.base import BaseCache


class CredentialRequestHandler(BaseHandler):
    """Message handler class for credential requests."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for credential requests.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug(f"CredentialRequestHandler called with context {context}")

        assert isinstance(context.message, CredentialRequest)

        self._logger.info(
            "Received credential request: %s", context.message.serialize(as_string=True)
        )

        if not context.connection_active:
            raise HandlerException("No connection established for credential request")

        credential_manager = CredentialManager(context)
        credential_exchange_record = await credential_manager.receive_request(
            context.message
        )

        # We cache some stuff in order to re-issue again in the future
        # without this roundtrip. It is used in credentials/manager.py
        cache: BaseCache = await context.inject(BaseCache)
        await cache.set(
            credential_exchange_record.credential_definition_id,
            credential_exchange_record.credential_exchange_id,
            600,
        )

        # If auto_issue is enabled, respond immediately
        if credential_exchange_record.auto_issue:
            (
                credential_exchange_record,
                credential_issue_message,
            ) = await credential_manager.issue_credential(
                credential_exchange_record, credential_exchange_record.credential_values
            )

            await responder.send_reply(credential_issue_message)
