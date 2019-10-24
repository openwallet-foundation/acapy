"""Basic message handler."""


from .....storage.error import StorageNotFoundError
from ....base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext
)
from ..manager import CredentialManager
from ..messages.credential_offer import CredentialOffer
from ..messages.credential_proposal import CredentialProposal
from ..models.credential_exchange import V10CredentialExchange


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

        self._logger.info(
            "Received credential offer: %s",
            context.message.serialize(as_string=True)
        )

        if not context.connection_ready:
            raise HandlerException("No connection established for credential offer")

        credential_manager = CredentialManager(context)

        indy_offer = context.message.indy_offer(0)
        credential_proposal_dict = CredentialProposal(
            comment=context.message.comment,
            credential_proposal=context.message.credential_preview,
            cred_def_id=indy_offer["cred_def_id"],
            schema_id=indy_offer["schema_id"]
        ).serialize()

        # Get credential exchange record (holder sent proposal first)
        # or create it (issuer sent offer first)
        try:
            credential_exchange_record = (
                await V10CredentialExchange.retrieve_by_tag_filter(
                    context,
                    {
                        "thread_id": context.message._thread_id,
                        "connection_id": context.connection_record.connection_id
                    }
                )
            )
            credential_exchange_record.credential_proposal_dict = (
                credential_proposal_dict
            )
        except StorageNotFoundError:  # issuer sent this offer free of any proposal
            credential_exchange_record = V10CredentialExchange(
                connection_id=context.connection_record.connection_id,
                thread_id=context.message._thread_id,
                initiator=V10CredentialExchange.INITIATOR_EXTERNAL,
                role=V10CredentialExchange.ROLE_HOLDER,
                credential_definition_id=indy_offer["cred_def_id"],
                schema_id=indy_offer["schema_id"],
                credential_proposal_dict=credential_proposal_dict
            )

        credential_exchange_record.credential_offer = indy_offer

        credential_exchange_record = await credential_manager.receive_offer(
            credential_exchange_record
        )

        # If auto respond is turned on, automatically reply with credential request
        if context.settings.get("debug.auto_respond_credential_offer"):
            (_, credential_request_message) = await credential_manager.create_request(
                credential_exchange_record=credential_exchange_record,
                holder_did=context.connection_record.my_did,
            )
            await responder.send_reply(credential_request_message)
