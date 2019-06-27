"""Classes to manage credentials."""

import asyncio
import json
import logging

from ....error import BaseError
from ....holder.base import BaseHolder
from ....issuer.base import BaseIssuer
from ....ledger.base import BaseLedger
from ....models.attach_decorator import AttachDecorator
from ....models.thread_decorator import ThreadDecorator

from ...connections.models.connection_record import ConnectionRecord
from ...request_context import RequestContext
from ...util import send_webhook

from .messages.credential_issue import CredentialIssue
from .messages.credential_offer import CredentialOffer
from .messages.credential_proposal import CredentialProposal
from .messages.credential_request import CredentialRequest
from .messages.inner.credential_preview import CredentialPreview
from .models.credential_exchange import V10CredentialExchange


class CredentialManagerError(BaseError):
    """Credential error."""


class CredentialManager:
    """Class for managing credentials."""

    def __init__(self, context: RequestContext):
        """
        Initialize a CredentialManager.

        Args:
            context: The context for this credential
        """
        self._context = context
        self._logger = logging.getLogger(__name__)

    @property
    def context(self) -> RequestContext:
        """
        Accessor for the current request context.

        Returns:
            The request context for this connection

        """
        return self._context

    async def create_proposal(
        self,
        connection_id: str,
        *,
        auto_offer: bool = None,
        comment: str = None,
        credential_preview: CredentialPreview = None,
        credential_definition_id: str
    ):
        """
        Create a credential proposal.

        Args:
            connection_id: Connection to create proposal for
            auto_offer: Should this proposal request automatically be handled to
                offer a credential
            credential_preview: The credential preview to use to create
                the credential proposal
            credential_definition_id: Credential definition id for the
                credential proposal

        Return:
            A tuple (credential_exchange, credential_proposal_message)

        """
        # Credential definition id must be present
        if not credential_definition_id:
            raise CredentialManagerError(
                "credential_definition_id is not set"
            )

        # Credential preview must be present
        if not credential_preview:
            raise CredentialManagerError(
                "credential_preview is not set"
            )

        ledger: BaseLedger = await self.context.inject(BaseLedger)
        async with ledger:
            credential_definition = await ledger.get_credential_definition(
                credential_definition_id
            )

        schema_id = credential_definition["schemaId"]
        credential_proposal_message = CredentialProposal(
            comment=comment,
            credential_proposal=credential_preview,
            schema_id=schema_id,
            cred_def_id=credential_definition_id)

        credential_exchange = V10CredentialExchange(
            connection_id=connection_id,
            thread_id=credential_proposal_message._thread_id,
            initiator=V10CredentialExchange.INITIATOR_SELF,
            state=V10CredentialExchange.STATE_PROPOSAL_SENT,
            credential_definition_id=credential_definition_id,
            schema_id=schema_id,
            credential_preview=credential_preview,
            auto_offer=auto_offer
        )
        await credential_exchange.save(self.context)
        asyncio.ensure_future(
            send_webhook("credentials", credential_exchange.serialize())
        )
        return credential_exchange, credential_proposal_message

    async def receive_proposal(
        self,
        credential_proposal_message: CredentialProposal,
        connection_id
    ):
        """
        Receive a credential proposal.

        Args:
            credential_proposal_message: Credential proposal to receive
            connection_id: Connection to receive offer on

        Returns:
            The credential_exchange_record

        """
        credential_proposal = json.loads(credential_proposal_message.offer_json)

        # go to cred def via ledger to get authoritative schema id
        cred_def_id = credential_proposal.get("cred_def_id", None)
        if cred_def_id:
            ledger: BaseLedger = await self.context.inject(BaseLedger)
            async with ledger:
                schema_id = await ledger.credential_definition_id2schema_id(cred_def_id)
        else:
            raise CredentialManagerError(
                "credential definition identifier is not set in proposal"
            )

        credential_exchange = V10CredentialExchange(
            connection_id=connection_id,
            thread_id=credential_proposal_message._thread_id,
            initiator=V10CredentialExchange.INITIATOR_EXTERNAL,
            state=V10CredentialExchange.STATE_PROPOSAL_RECEIVED,
            credential_definition_id=cred_def_id,
            schema_id=schema_id,
            credential_preview=credential_proposal,
        )
        await credential_exchange.save(self.context)
        asyncio.ensure_future(
            send_webhook("credentials", credential_exchange.serialize())
        )

        return credential_exchange

    async def create_offer(
        self,
        credential_exchange_record: V10CredentialExchange,
        *,
        comment=None
    ):
        """
        Create a credential offer.

        Args:
            credential_exchange_record: Credential exchange to create offer for
            comment: Optional human-readable comment pertaining to offer creation

        Return:
            A tuple (credential_exchange, credential_offer_message)

        """
        credential_definition_id = credential_exchange_record.credential_definition_id

        issuer: BaseIssuer = await self.context.inject(BaseIssuer)
        credential_offer = await issuer.create_credential_offer(
            credential_definition_id
        )

        credential_offer_message = CredentialOffer(
            comment=comment,
            credential_preview=credential_exchange_record.credential_preview,
            offers_attach=[AttachDecorator.from_indy_dict(credential_offer)]
        )

        # TODO: Find a more elegant way to do this?
        credential_offer_message._thread = ThreadDecorator(
            thid=credential_exchange_record.thread_id
        )

        credential_exchange_record.thread_id = credential_offer_message._thread_id
        credential_exchange_record.schema_id = credential_offer["schema_id"]
        credential_exchange_record.credential_definition_id = (
            credential_offer["cred_def_id"]
        )
        credential_exchange_record.state = V10CredentialExchange.STATE_OFFER_SENT
        credential_exchange_record.credential_offer = credential_offer
        await credential_exchange_record.save(self.context)
        asyncio.ensure_future(
            send_webhook("credentials", credential_exchange_record.serialize())
        )

        return credential_exchange_record, credential_offer_message

    async def receive_offer(
        self,
        credential_exchange_record: V10CredentialExchange,
    ):
        """
        Receive a credential offer.

        Args:
            credential_exchange_record: Credential exchange record with offer to receive

        Returns:
            The credential_exchange_record

        """
        # Holder adds or updates MIME types per attribute from cred preview if need be
        ledger: BaseLedger = await self.context.inject(BaseLedger)
        async with ledger:
            credential_definition = await ledger.get_credential_definition(
                credential_exchange_record.credential_definition_id
            )
        holder: BaseHolder = await self.context.inject(BaseHolder)
        await holder.store_mime_types(
            credential_definition,
            credential_exchange_record.credential_preview.mime_type_dict()
        )

        credential_exchange_record.state = V10CredentialExchange.STATE_OFFER_RECEIVED
        await credential_exchange_record.save(self.context)

        asyncio.ensure_future(
            send_webhook("credentials", credential_exchange_record.serialize())
        )

        return credential_exchange_record

    async def create_request(
        self,
        credential_exchange_record: V10CredentialExchange,
        connection_record: ConnectionRecord
    ):
        """
        Create a credential request.

        Args:
            credential_exchange_record: Credential exchange to create request for
            connection_record: Connection to create the request for

        Return:
            A tuple (credential_exchange_record, credential_request_message)

        """
        credential_definition_id = credential_exchange_record.credential_definition_id
        credential_offer = credential_exchange_record.credential_offer

        did = connection_record.my_did

        ledger: BaseLedger = await self.context.inject(BaseLedger)
        async with ledger:
            credential_definition = await ledger.get_credential_definition(
                credential_definition_id
            )

        holder: BaseHolder = await self.context.inject(BaseHolder)
        (
            credential_request,
            credential_request_metadata,
        ) = await holder.create_credential_request(
            credential_offer, credential_definition, did
        )

        credential_request_message = CredentialRequest(
            requests_attach=[AttachDecorator.from_indy_dict(credential_request)]
        )

        # TODO: Find a more elegant way to do this?
        credential_request_message._thread = ThreadDecorator(
            thid=credential_exchange_record.thread_id
        )

        credential_exchange_record.state = V10CredentialExchange.STATE_REQUEST_SENT
        credential_exchange_record.credential_request = credential_request
        credential_exchange_record.credential_request_metadata = (
            credential_request_metadata
        )
        await credential_exchange_record.save(self.context)
        asyncio.ensure_future(
            send_webhook("credentials", credential_exchange_record.serialize())
        )

        return credential_exchange_record, credential_request_message

    async def receive_request(
        self,
        credential_request_message: CredentialRequest
    ):
        """
        Receive a credential request.

        Args:
            credential_request_message: Credential request to receive

        """

        assert len(credential_request_message.offers_attach or []) == 1
        credential_request = credential_request_message.indy_cred_req(0)

        credential_exchange_record = await V10CredentialExchange.retrieve_by_tag_filter(
            self.context,
            tag_filter={"thread_id": credential_request_message._thread_id},
        )

        credential_exchange_record.credential_request = credential_request
        credential_exchange_record.state = V10CredentialExchange.STATE_REQUEST_RECEIVED
        await credential_exchange_record.save(self.context)
        asyncio.ensure_future(
            send_webhook("credentials", credential_exchange_record.serialize())
        )

        return credential_exchange_record

    async def issue_credential(
        self,
        credential_exchange_record: V10CredentialExchange,
        *,
        comment: str = None,
        credential_values: dict
    ):
        """
        Issue a credential.

        Args:
            credential_exchange_record: The credential exchange we are issuing a
                credential for
            credential_values: dict of credential attribute {name: value} pairs

        Returns:
            Tuple: (Updated credential exchange record, credential message obj)

        """
        schema_id = credential_exchange_record.schema_id
        credential_offer = credential_exchange_record.credential_offer
        credential_request = credential_exchange_record.credential_request

        ledger: BaseLedger = await self.context.inject(BaseLedger)
        async with ledger:
            schema = await ledger.get_schema(schema_id)

        issuer: BaseIssuer = await self.context.inject(BaseIssuer)
        (credential, _credential_revocation_id) = await issuer.create_credential(
            schema, credential_offer, credential_request, credential_values
        )

        credential_exchange_record.state = V10CredentialExchange.STATE_ISSUED
        await credential_exchange_record.save(self.context)
        asyncio.ensure_future(
            send_webhook("credentials", credential_exchange_record.serialize())
        )

        credential_message = CredentialIssue(
            comment=comment,
            credentials_attach=[AttachDecorator.from_indy_dict(credential)]
        )

        # TODO: Find a more elegant way to do this?
        credential_message._thread = ThreadDecorator(
            thid=credential_exchange_record.thread_id
        )

        return credential_exchange_record, credential_message

    async def store_credential(
        self,
        credential_message: CredentialIssue
    ):
        """
        Store a credential in the wallet.

        Args:
            credential_message: credential to store

        """
        assert len(credential_message.credentials_attach or []) == 1
        credential = credential_message.indy_credential(0)

        credential_exchange_record = await V10CredentialExchange.retrieve_by_tag_filter(
            self.context, tag_filter={"thread_id": credential_message._thread_id}
        )

        ledger: BaseLedger = await self.context.inject(BaseLedger)
        async with ledger:
            credential_definition = await ledger.get_credential_definition(
                credential["cred_def_id"]
            )

        holder: BaseHolder = await self.context.inject(BaseHolder)
        credential_id = await holder.store_credential(
            credential_definition,
            credential,
            credential_exchange_record.credential_request_metadata,
        )

        wallet_credential = await holder.get_credential(credential_id)

        credential_exchange_record.state = V10CredentialExchange.STATE_STORED
        credential_exchange_record.credential_id = credential_id
        credential_exchange_record.credential = wallet_credential
        await credential_exchange_record.save(self.context)
        asyncio.ensure_future(
            send_webhook("credentials", credential_exchange_record.serialize())
        )
