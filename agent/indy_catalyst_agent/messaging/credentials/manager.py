"""Classes to manage credentials."""

import asyncio
import json
import logging

from ...error import BaseError
from ...holder.base import BaseHolder
from ...issuer.base import BaseIssuer
from ...ledger.base import BaseLedger
from ...models.thread_decorator import ThreadDecorator

from ..connections.models.connection_record import ConnectionRecord
from ..request_context import RequestContext

from .messages.credential_issue import CredentialIssue
from .messages.credential_request import CredentialRequest
from .messages.credential_offer import CredentialOffer
from .models.credential_exchange import CredentialExchange

from ..util import send_webhook


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

    async def create_offer(self, credential_definition_id, connection_id):
        """
        Create an offer.

        Args:
            credential_definition_id: Credential definition id for offer
            connection_id: Connection to create offer for

        Returns:
            A tuple (credential_exchange, credential_offer_message)

        """
        issuer: BaseIssuer = await self.context.inject(BaseIssuer)
        credential_offer = issuer.create_credential_offer(credential_definition_id)

        credential_offer_message = CredentialOffer(
            offer_json=json.dumps(credential_offer)
        )

        credential_exchange = CredentialExchange(
            connection_id=connection_id,
            thread_id=credential_offer_message._thread_id,
            initiator=CredentialExchange.INITIATOR_SELF,
            state=CredentialExchange.STATE_OFFER_SENT,
            credential_definition_id=credential_definition_id,
            schema_id=credential_offer["schema_id"],
            credential_offer=credential_offer,
        )
        await credential_exchange.save(self.context)
        asyncio.ensure_future(
            send_webhook("credentials", credential_exchange.serialize())
        )
        return credential_exchange, credential_offer_message

    async def receive_offer(
        self, credential_offer_message: CredentialOffer, connection_id
    ):
        """
        Receive a credential offer.

        Args:
            credential_offer: Credential offer to receive
            connection_id: Connection to receive offer on

        """

        credential_offer = json.loads(credential_offer_message.offer_json)

        credential_exchange = CredentialExchange(
            connection_id=connection_id,
            thread_id=credential_offer_message._thread_id,
            initiator=CredentialExchange.INITIATOR_EXTERNAL,
            state=CredentialExchange.STATE_OFFER_RECEIVED,
            credential_definition_id=credential_offer["cred_def_id"],
            schema_id=credential_offer["schema_id"],
            credential_offer=credential_offer,
        )
        await credential_exchange.save(self.context)
        asyncio.ensure_future(
            send_webhook("credentials", credential_exchange.serialize())
        )

    async def create_request(
        self,
        credential_exchange_record: CredentialExchange,
        connection_record: ConnectionRecord,
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
            request=json.dumps(credential_request)
        )

        # TODO: Find a more elegant way to do this
        thread = ThreadDecorator(thid=credential_exchange_record.thread_id)
        credential_request_message._thread = thread

        credential_exchange_record.state = CredentialExchange.STATE_REQUEST_SENT
        credential_exchange_record.credential_request = credential_request
        credential_exchange_record.credential_request_metadata = (
            credential_request_metadata
        )
        await credential_exchange_record.save(self.context)
        asyncio.ensure_future(
            send_webhook("credentials", credential_exchange_record.serialize())
        )

        return credential_exchange_record, credential_request_message

    async def receive_request(self, credential_request_message: CredentialRequest):
        """
        Receive a credential request.

        Args:
            credential_request_message: Credential request to receive

        """

        credential_request = json.loads(credential_request_message.request)

        credential_exchange_record = await CredentialExchange.retrieve_by_tag_filter(
            self.context,
            tag_filter={"thread_id": credential_request_message._thread_id},
        )

        credential_exchange_record.credential_request = credential_request
        credential_exchange_record.state = CredentialExchange.STATE_REQUEST_RECEIVED
        await credential_exchange_record.save(self.context)
        asyncio.ensure_future(
            send_webhook("credentials", credential_exchange_record.serialize())
        )

    async def issue_credential(
        self, credential_exchange_record: CredentialExchange, credential_values: dict
    ):
        """
        Issue a credential.

        Args:
            credential_exchange_record: The credential exchange we are issuing a
                credential for
            credential_values: dict of credential values

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
        (credential, credential_revocation_id) = await issuer.create_credential(
            schema, credential_offer, credential_request, credential_values
        )

        credential_exchange_record.state = CredentialExchange.STATE_ISSUED
        await credential_exchange_record.save(self.context)
        asyncio.ensure_future(
            send_webhook("credentials", credential_exchange_record.serialize())
        )

        credential_message = CredentialIssue(issue=json.dumps(credential))

        # TODO: Find a more elegant way to do this
        thread = ThreadDecorator(thid=credential_exchange_record.thread_id)
        credential_message._thread = thread

        return credential_exchange_record, credential_message

    async def store_credential(self, credential_message: CredentialIssue):
        """
        Store a credential in the wallet.

        Args:
            credential_message: credential to store

        """
        credential = json.loads(credential_message.issue)

        credential_exchange_record = await CredentialExchange.retrieve_by_tag_filter(
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

        credential_exchange_record.state = CredentialExchange.STATE_STORED
        credential_exchange_record.credential_id = credential_id
        await credential_exchange_record.save(self.context)
        asyncio.ensure_future(
            send_webhook("credentials", credential_exchange_record.serialize())
        )
