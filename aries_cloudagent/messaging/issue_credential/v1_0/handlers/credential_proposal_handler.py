"""Credential proposal handler."""


from ....base_handler import (
    BaseHandler,
    BaseResponder,
    HandlerException,
    RequestContext
)

from ..manager import CredentialManager
from ..messages.credential_proposal import CredentialProposal


class CredentialProposalHandler(BaseHandler):
    """Message handler class for credential proposals."""

    async def handle(self, context: RequestContext, responder: BaseResponder):
        """
        Message handler logic for credential proposals.

        Args:
            context: proposal context
            responder: responder callback
        """
        self._logger.debug(f"CredentialProposalHandler called with context {context}")

        assert isinstance(context.message, CredentialProposal)

        self._logger.info(
            "Received credential proposal: %s",
            context.message.serialize(as_string=True)
        )

        if not context.connection_ready:
            raise HandlerException("No connection established for credential proposal")

        credential_manager = CredentialManager(context)
        credential_exchange_record = await credential_manager.receive_proposal(
            credential_proposal_message=context.message,
            connection_id=context.connection_record.connection_id
        )

        # If auto_offer is enabled, respond immediately with offer
        if credential_exchange_record.auto_offer:
            (
                credential_exchange_record,
                credential_offer_message,
            ) = await credential_manager.create_offer(
                credential_exchange_record,
                comment=context.message.comment
            )

            await responder.send_reply(credential_offer_message)
