"""Basic message handler."""

from ....messaging.base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext,
)

from ..manager import CredentialManager
from ..messages.credential_offer import CredentialOffer


class CredentialOfferHandler(BaseHandler):
    """Message handler class for credential offers."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for credential offers.

        Args:
            context: request context
            responder: responder callback
        """
        self._logger.debug(f"CredentialOfferHandler called with context {context}")

        assert isinstance(context.message, CredentialOffer)

        self._logger.info("Received credential offer: %s", context.message.offer_json)

        if not context.connection_ready:
            raise HandlerException("No connection established for credential offer")

        credential_manager = CredentialManager(context)

        credential_exchange_record = await credential_manager.receive_offer(
            context.message, context.connection_record.connection_id
        )

        # If auto respond is turned on, automatically reply with credential request
        if context.settings.get("debug.auto_respond_credential_offer"):
            (_, credential_request_message) = await credential_manager.create_request(
                credential_exchange_record, context.connection_record
            )
            await responder.send_reply(credential_request_message)
