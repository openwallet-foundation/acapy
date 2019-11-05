"""Classes to manage credentials."""

import logging
from typing import Tuple

from ....config.injection_context import InjectionContext
from ....error import BaseError
from ....holder.base import BaseHolder
from ....issuer.base import BaseIssuer
from ....ledger.base import BaseLedger
from ....storage.error import StorageNotFoundError

from .messages.credential_issue import CredentialIssue
from .messages.credential_offer import CredentialOffer
from .messages.credential_proposal import CredentialProposal
from .messages.credential_request import CredentialRequest
from .messages.credential_stored import CredentialStored
from .messages.inner.credential_preview import CredentialPreview
from .models.credential_exchange import V10CredentialExchange


class CredentialManagerError(BaseError):
    """Credential error."""


class CredentialManager:
    """Class for managing credentials."""

    def __init__(self, context: InjectionContext):
        """
        Initialize a CredentialManager.

        Args:
            context: The context for this credential
        """
        self._context = context
        self._logger = logging.getLogger(__name__)

    @property
    def context(self) -> InjectionContext:
        """
        Accessor for the current request context.

        Returns:
            The request context for this connection

        """
        return self._context

    async def prepare_send(
        self, connection_id: str, credential_proposal: CredentialProposal
    ) -> Tuple[V10CredentialExchange, CredentialOffer]:
        """
        Set up a new credential exchange for an automated send.

        Args:
            connection_id: Connection to create offer for
            credential_proposal: The credential proposal with preview on
                attribute values to use if auto_issue is enabled

        Returns:
            A tuple of the new credential exchange record and credential offer message

        """

        credential_definition_id = credential_proposal.cred_def_id
        if not credential_definition_id:
            raise CredentialManagerError(
                "Proposal credential definition ID is required"
            )

        credential_exchange = V10CredentialExchange(
            auto_issue=True,
            connection_id=connection_id,
            initiator=V10CredentialExchange.INITIATOR_SELF,
            role=V10CredentialExchange.ROLE_ISSUER,
            credential_definition_id=credential_definition_id,
            credential_proposal_dict=credential_proposal.serialize(),
        )
        (credential_exchange, credential_offer) = await self.create_offer(
            credential_exchange_record=credential_exchange,
            comment="create automated credential exchange",
        )
        return credential_exchange, credential_offer

    async def create_proposal(
        self,
        connection_id: str,
        *,
        auto_offer: bool = None,
        comment: str = None,
        credential_preview: CredentialPreview = None,
        credential_definition_id: str,
    ) -> V10CredentialExchange:
        """
        Create a credential proposal.

        Args:
            connection_id: Connection to create proposal for
            auto_offer: Should this proposal request automatically be handled to
                offer a credential
            comment: Optional human-readable comment to include in proposal
            credential_preview: The credential preview to use to create
                the credential proposal
            credential_definition_id: Credential definition id for the
                credential proposal

        Returns:
            Resulting credential exchange record including credential proposal

        """
        # Credential definition id must be present
        if not credential_definition_id:
            raise CredentialManagerError("credential_definition_id is not set")

        # Credential preview must be present
        if not credential_preview:
            raise CredentialManagerError("credential_preview is not set")

        ledger: BaseLedger = await self.context.inject(BaseLedger)
        async with ledger:
            schema_id = await ledger.credential_definition_id2schema_id(
                credential_definition_id
            )

        credential_proposal_message = CredentialProposal(
            comment=comment,
            credential_proposal=credential_preview,
            schema_id=schema_id,
            cred_def_id=credential_definition_id,
        )

        credential_exchange_record = V10CredentialExchange(
            connection_id=connection_id,
            thread_id=credential_proposal_message._thread_id,
            initiator=V10CredentialExchange.INITIATOR_SELF,
            role=V10CredentialExchange.ROLE_HOLDER,
            state=V10CredentialExchange.STATE_PROPOSAL_SENT,
            credential_definition_id=credential_definition_id,
            schema_id=schema_id,
            credential_proposal_dict=credential_proposal_message.serialize(),
            auto_offer=auto_offer,
        )
        await credential_exchange_record.save(
            self.context, reason="create credential proposal"
        )
        return credential_exchange_record

    async def receive_proposal(self) -> V10CredentialExchange:
        """
        Receive a credential proposal from message in context on manager creation.

        Returns:
            The resulting credential exchange record, created

        """
        # go to cred def via ledger to get authoritative schema id
        credential_proposal_message = self.context.message
        connection_id = self.context.connection_record.connection_id
        cred_def_id = credential_proposal_message.cred_def_id
        if cred_def_id:
            ledger: BaseLedger = await self.context.inject(BaseLedger)
            async with ledger:
                schema_id = await ledger.credential_definition_id2schema_id(cred_def_id)
        else:
            raise CredentialManagerError(
                "credential definition identifier is not set in proposal"
            )

        credential_exchange_record = V10CredentialExchange(
            connection_id=connection_id,
            thread_id=credential_proposal_message._thread_id,
            initiator=V10CredentialExchange.INITIATOR_EXTERNAL,
            role=V10CredentialExchange.ROLE_ISSUER,
            state=V10CredentialExchange.STATE_PROPOSAL_RECEIVED,
            credential_definition_id=cred_def_id,
            schema_id=schema_id,
            credential_proposal_dict=credential_proposal_message.serialize(),
            auto_offer=self.context.settings.get(
                "debug.auto_respond_credential_proposal"
            ),
            auto_issue=self.context.settings.get(
                "debug.auto_respond_credential_request"
            ),
        )
        await credential_exchange_record.save(
            self.context, reason="receive credential proposal"
        )

        return credential_exchange_record

    async def create_offer(
        self, credential_exchange_record: V10CredentialExchange, comment: str = None
    ) -> Tuple[V10CredentialExchange, CredentialOffer]:
        """
        Create a credential offer, update credential exchange record.

        Args:
            credential_exchange_record: Credential exchange to create offer for
            comment: optional human-readable comment to set in offer message

        Returns:
            A tuple (credential exchange record, credential offer message)

        """
        credential_definition_id = credential_exchange_record.credential_definition_id
        if credential_exchange_record.credential_proposal_dict:
            cred_preview = CredentialProposal.deserialize(
                credential_exchange_record.credential_proposal_dict
            ).credential_proposal
        else:
            cred_preview = None

        cache_key = f"credential_offer::{credential_definition_id}"
        cached = await V10CredentialExchange.get_cached_key(self.context, cache_key)
        if cached:
            credential_offer = cached["offer"]
        else:
            issuer: BaseIssuer = await self.context.inject(BaseIssuer)
            credential_offer = await issuer.create_credential_offer(
                credential_definition_id
            )
            await V10CredentialExchange.set_cached_key(
                self.context, cache_key, {"offer": credential_offer}, 3600
            )

        credential_offer_message = CredentialOffer(
            comment=comment,
            credential_preview=cred_preview,
            offers_attach=[CredentialOffer.wrap_indy_offer(credential_offer)],
        )

        credential_offer_message._thread = {
            "thid": credential_exchange_record.thread_id
        }

        credential_exchange_record.thread_id = credential_offer_message._thread_id
        credential_exchange_record.schema_id = credential_offer["schema_id"]
        credential_exchange_record.credential_definition_id = credential_offer[
            "cred_def_id"
        ]
        credential_exchange_record.state = V10CredentialExchange.STATE_OFFER_SENT
        credential_exchange_record.credential_offer = credential_offer
        await credential_exchange_record.save(
            self.context, reason="create credential offer"
        )

        return (credential_exchange_record, credential_offer_message)

    async def receive_offer(self) -> V10CredentialExchange:
        """
        Receive a credential offer.

        Returns:
            The credential exchange record, updated

        """
        credential_offer_message: CredentialOffer = self.context.message
        connection_id = self.context.connection_record.connection_id

        credential_preview = credential_offer_message.credential_preview
        indy_offer = credential_offer_message.indy_offer(0)

        if credential_preview:
            credential_proposal_dict = CredentialProposal(
                comment=credential_offer_message.comment,
                credential_proposal=credential_preview,
                cred_def_id=indy_offer["cred_def_id"],
                schema_id=indy_offer["schema_id"],
            ).serialize()
        else:
            credential_proposal_dict = None

        # Get credential exchange record (holder sent proposal first)
        # or create it (issuer sent offer first)
        try:
            (
                credential_exchange_record
            ) = await V10CredentialExchange.retrieve_by_connection_and_thread(
                self.context, connection_id, credential_offer_message._thread_id
            )
            credential_exchange_record.credential_proposal_dict = (
                credential_proposal_dict
            )
        except StorageNotFoundError:  # issuer sent this offer free of any proposal
            credential_exchange_record = V10CredentialExchange(
                connection_id=connection_id,
                thread_id=credential_offer_message._thread_id,
                initiator=V10CredentialExchange.INITIATOR_EXTERNAL,
                role=V10CredentialExchange.ROLE_HOLDER,
                credential_definition_id=indy_offer["cred_def_id"],
                schema_id=indy_offer["schema_id"],
                credential_proposal_dict=credential_proposal_dict,
            )

        credential_exchange_record.credential_offer = indy_offer
        credential_exchange_record.state = V10CredentialExchange.STATE_OFFER_RECEIVED

        await credential_exchange_record.save(
            self.context, reason="receive credential offer"
        )

        return credential_exchange_record

    async def create_request(
        self, credential_exchange_record: V10CredentialExchange, holder_did: str
    ) -> Tuple[V10CredentialExchange, CredentialRequest]:
        """
        Create a credential request.

        Args:
            credential_exchange_record: Credential exchange record
                for which to create request
            holder_did: holder DID

        Returns:
            A tuple (credential exchange record, credential request message)

        """
        credential_definition_id = credential_exchange_record.credential_definition_id
        credential_offer = credential_exchange_record.credential_offer

        if credential_exchange_record.credential_request:
            self._logger.warning(
                "create_request called multiple times for v1.0 credential exchange: %s",
                credential_exchange_record.credential_exchange_id,
            )
        else:
            if "nonce" not in credential_offer:
                raise CredentialManagerError("Missing nonce in credential offer")
            nonce = credential_offer["nonce"]
            cache_key = (
                f"credential_request::{credential_definition_id}::{holder_did}::{nonce}"
            )
            cached = await V10CredentialExchange.get_cached_key(self.context, cache_key)
            if cached:
                (
                    credential_exchange_record.credential_request,
                    credential_exchange_record.credential_request_metadata,
                ) = (cached["request"], cached["metadata"])
            else:
                ledger: BaseLedger = await self.context.inject(BaseLedger)
                async with ledger:
                    credential_definition = await ledger.get_credential_definition(
                        credential_definition_id
                    )

                holder: BaseHolder = await self.context.inject(BaseHolder)
                (
                    credential_exchange_record.credential_request,
                    credential_exchange_record.credential_request_metadata,
                ) = await holder.create_credential_request(
                    credential_offer, credential_definition, holder_did
                )

                await V10CredentialExchange.set_cached_key(
                    self.context,
                    cache_key,
                    {
                        "request": credential_exchange_record.credential_request,
                        "metadata": (
                            credential_exchange_record.credential_request_metadata
                        ),
                    },
                    7200,
                )

        credential_request_message = CredentialRequest(
            requests_attach=[
                CredentialRequest.wrap_indy_cred_req(
                    credential_exchange_record.credential_request
                )
            ]
        )
        credential_request_message._thread = {
            "thid": credential_exchange_record.thread_id
        }

        credential_exchange_record.state = V10CredentialExchange.STATE_REQUEST_SENT
        await credential_exchange_record.save(
            self.context, reason="create credential request"
        )

        return credential_exchange_record, credential_request_message

    async def receive_request(self):
        """
        Receive a credential request.

        Args:
            credential_request_message: Credential request to receive

        Returns:
            credential exchange record, retrieved and updated

        """
        credential_request_message = self.context.message
        assert len(credential_request_message.requests_attach or []) == 1
        credential_request = credential_request_message.indy_cred_req(0)

        (
            credential_exchange_record
        ) = await V10CredentialExchange.retrieve_by_connection_and_thread(
            self.context,
            self.context.connection_record.connection_id,
            credential_request_message._thread_id,
        )
        credential_exchange_record.credential_request = credential_request
        credential_exchange_record.state = V10CredentialExchange.STATE_REQUEST_RECEIVED
        await credential_exchange_record.save(
            self.context, reason="receive credential request"
        )

        return credential_exchange_record

    async def issue_credential(
        self,
        credential_exchange_record: V10CredentialExchange,
        *,
        comment: str = None,
        credential_values: dict,
    ) -> Tuple[V10CredentialExchange, CredentialIssue]:
        """
        Issue a credential.

        Args:
            credential_exchange_record: The credential exchange record
                for which to issue a credential
            comment: optional human-readable comment pertaining to credential issue
            credential_values: dict of credential attribute {name: value} pairs

        Returns:
            Tuple: (Updated credential exchange record, credential message)

        """
        schema_id = credential_exchange_record.schema_id

        if credential_exchange_record.credential:
            self._logger.warning(
                "issue_credential called multiple times for "
                + "v1.0 credential exchange: %s",
                credential_exchange_record.credential_exchange_id,
            )
        else:
            credential_offer = credential_exchange_record.credential_offer
            credential_request = credential_exchange_record.credential_request

            ledger: BaseLedger = await self.context.inject(BaseLedger)
            async with ledger:
                schema = await ledger.get_schema(schema_id)

            issuer: BaseIssuer = await self.context.inject(BaseIssuer)
            (
                credential_exchange_record.credential,
                _,  # credential_revocation_id
            ) = await issuer.create_credential(
                schema, credential_offer, credential_request, credential_values
            )

        credential_exchange_record.state = V10CredentialExchange.STATE_ISSUED
        await credential_exchange_record.save(self.context, reason="receive credential")

        credential_message = CredentialIssue(
            comment=comment,
            credentials_attach=[
                CredentialIssue.wrap_indy_credential(
                    credential_exchange_record.credential
                )
            ],
        )
        credential_message._thread = {"thid": credential_exchange_record.thread_id}

        return (credential_exchange_record, credential_message)

    async def receive_credential(self) -> V10CredentialExchange:
        """
        Receive a credential from an issuer.

        Hold in storage potentially to be processed by controller before storing.

        Returns:
            Credential exchange record, retrieved and updated

        """
        credential_message = self.context.message
        assert len(credential_message.credentials_attach or []) == 1
        raw_credential = credential_message.indy_credential(0)

        (
            credential_exchange_record
        ) = await V10CredentialExchange.retrieve_by_connection_and_thread(
            self.context,
            self.context.connection_record.connection_id,
            credential_message._thread_id,
        )

        credential_exchange_record.raw_credential = raw_credential
        credential_exchange_record.state = (
            V10CredentialExchange.STATE_CREDENTIAL_RECEIVED
        )

        await credential_exchange_record.save(self.context, reason="receive credential")
        return credential_exchange_record

    async def store_credential(
        self, credential_exchange_record: V10CredentialExchange
    ) -> Tuple[V10CredentialExchange, CredentialStored]:
        """
        Store a credential in the wallet.

        Args:
            credential_exchange_record: credential exchange record
                with credential to store

        Returns:
            Tuple: (Updated credential exchange record, credential-stored message)

        """
        raw_credential = credential_exchange_record.raw_credential

        ledger: BaseLedger = await self.context.inject(BaseLedger)
        async with ledger:
            credential_definition = await ledger.get_credential_definition(
                raw_credential["cred_def_id"]
            )

        holder: BaseHolder = await self.context.inject(BaseHolder)
        credential_id = await holder.store_credential(
            credential_definition,
            raw_credential,
            credential_exchange_record.credential_request_metadata,
            CredentialPreview.deserialize(
                credential_exchange_record.credential_proposal_dict[
                    "credential_proposal"
                ]
            ).mime_types(),
        )

        credential = await holder.get_credential(credential_id)

        credential_exchange_record.state = V10CredentialExchange.STATE_STORED
        credential_exchange_record.credential_id = credential_id
        credential_exchange_record.credential = credential
        await credential_exchange_record.save(self.context, reason="store credential")

        credential_stored_message = CredentialStored()
        credential_stored_message.assign_thread_id(credential_exchange_record.thread_id)

        # Delete the exchange record since we're done with it
        await credential_exchange_record.delete_record(self.context)

        return credential_exchange_record, credential_stored_message

    async def credential_stored(self) -> V10CredentialExchange:
        """
        Receive confirmation that holder stored credential.

        Returns:
            credential exchange record, retrieved and updated

        """
        credential_stored_message = self.context.message
        (
            credential_exchange_record
        ) = await V10CredentialExchange.retrieve_by_connection_and_thread(
            self.context,
            self.context.connection_record.connection_id,
            credential_stored_message._thread_id,
        )

        credential_exchange_record.state = V10CredentialExchange.STATE_STORED
        await credential_exchange_record.save(self.context, reason="credential stored")

        # We're done with the exchange so delete
        await credential_exchange_record.delete_record(self.context)

        return credential_exchange_record
