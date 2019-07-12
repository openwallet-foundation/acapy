"""Classes to manage credentials."""

import asyncio
import json
import logging
import time

from ...config.injection_context import InjectionContext
from ...error import BaseError
from ...cache.base import BaseCache
from ...holder.base import BaseHolder
from ...issuer.base import BaseIssuer
from ...ledger.base import BaseLedger
from ...storage.error import StorageNotFoundError

from ..connections.models.connection_record import ConnectionRecord
from ..responder import BaseResponder

from .messages.credential_issue import CredentialIssue
from .messages.credential_request import CredentialRequest
from .messages.credential_offer import CredentialOffer
from .models.credential_exchange import CredentialExchange


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
        Accessor for the current injection context.

        Returns:
            The injection context for this credential manager

        """
        return self._context

    async def cache_credential_exchange(
        self, credential_exchange_record: CredentialExchange
    ):
        """Cache a credential exchange to avoid redundant credential requests."""
        cache: BaseCache = await self.context.inject(BaseCache)
        await cache.set(
            "credential_exchange::"
            + f"{credential_exchange_record.credential_definition_id}::"
            + f"{credential_exchange_record.connection_id}",
            credential_exchange_record.credential_exchange_id,
            600,
        )

    async def prepare_send(
        self, credential_definition_id: str, connection_id: str, credential_values: dict
    ) -> CredentialExchange:
        """
        Set up a new credential exchange for an automated send.

        Args:
            credential_definition_id: Credential definition id for offer
            connection_id: Connection to create offer for
            credential_values: The credential values to use if auto_issue is enabled

        Returns:
            A new `CredentialExchange` record

        """

        cache: BaseCache = await self._context.inject(BaseCache)

        # This cache is populated in credential_request_handler.py
        # Do we have a source (parent) credential exchange for which
        # we can re-use the credential request/offer?
        source_credential_exchange_id = await cache.get(
            "credential_exchange::"
            + f"{credential_definition_id}::"
            + f"{connection_id}"
        )

        source_credential_exchange = None

        if source_credential_exchange_id:

            # The cached credential exchange ID may not have an associated credential
            # request yet. Wait up to 30 seconds for that to be populated, then
            # move on and replace it as the cached credential exchange

            lookup_start = time.perf_counter()
            while True:
                source_credential_exchange = await CredentialExchange.retrieve_by_id(
                    self._context, source_credential_exchange_id
                )
                if source_credential_exchange.credential_request:
                    break
                if lookup_start + 30 < time.perf_counter():
                    source_credential_exchange = None
                    break
                await asyncio.sleep(0.3)

        if source_credential_exchange:

            # Since we have the source exchange cache, we can re-use the schema_id,
            # credential_offer, and credential_request to save a roundtrip
            credential_exchange = CredentialExchange(
                auto_issue=True,
                connection_id=connection_id,
                initiator=CredentialExchange.INITIATOR_SELF,
                state=CredentialExchange.STATE_REQUEST_RECEIVED,
                credential_definition_id=credential_definition_id,
                schema_id=source_credential_exchange.schema_id,
                credential_offer=source_credential_exchange.credential_offer,
                credential_request=source_credential_exchange.credential_request,
                credential_values=credential_values,
                # We use the source credential exchange's thread id as the parent
                # thread id. This thread is a branch of that parent so that the other
                # agent can use the parent thread id to look up its corresponding
                # source credential exchange object as needed
                parent_thread_id=source_credential_exchange.thread_id,
            )
            await credential_exchange.save(self.context)
            await self.updated_record(credential_exchange)

        else:
            # If the cache is empty, we must use the normal credential flow while
            # also instructing the agent to automatically issue the credential
            # once it receives the credential request

            credential_exchange = await self.create_offer(
                credential_definition_id, connection_id, True, credential_values
            )

            # Mark this credential exchange as the current cached one for this cred def
            await self.cache_credential_exchange(credential_exchange)

        return credential_exchange

    async def perform_send(
        self, credential_exchange: CredentialExchange, outbound_handler
    ):
        """Send the first message in a credential exchange."""

        if credential_exchange.credential_request:
            (credential_exchange, credential_message) = await self.issue_credential(
                credential_exchange
            )
            await outbound_handler(
                credential_message, connection_id=credential_exchange.connection_id
            )
        else:
            credential_exchange, credential_offer_message = await self.offer_credential(
                credential_exchange
            )
            await outbound_handler(
                credential_offer_message,
                connection_id=credential_exchange.connection_id,
            )

    async def create_offer(
        self,
        credential_definition_id: str,
        connection_id: str,
        auto_issue: bool = None,
        credential_values: dict = None,
    ):
        """
        Create a new credential exchange representing an offer.

        Args:
            credential_definition_id: Credential definition id for offer
            connection_id: Connection to create offer for

        Returns:
            A new credential exchange record

        """

        issuer: BaseIssuer = await self.context.inject(BaseIssuer)
        credential_offer = await issuer.create_credential_offer(
            credential_definition_id
        )

        credential_exchange = CredentialExchange(
            auto_issue=auto_issue,
            connection_id=connection_id,
            initiator=CredentialExchange.INITIATOR_SELF,
            state=CredentialExchange.STATE_OFFER_SENT,
            credential_definition_id=credential_definition_id,
            schema_id=credential_offer["schema_id"],
            credential_offer=credential_offer,
            credential_values=credential_values,
        )
        await credential_exchange.save(self.context)
        await self.updated_record(credential_exchange)
        return credential_exchange

    async def offer_credential(self, credential_exchange: CredentialExchange):
        """
        Offer a credential.

        Args:
            credential_exchange_record: The credential exchange we are creating
                the credential offer for

        Returns:
            Tuple: (Updated credential exchange record, credential offer message)

        """
        credential_offer_message = CredentialOffer(
            offer_json=json.dumps(credential_exchange.credential_offer)
        )
        credential_exchange.thread_id = credential_offer_message._thread_id
        credential_exchange.state = CredentialExchange.STATE_OFFER_SENT
        await credential_exchange.save(self.context)
        await self.updated_record(credential_exchange)
        return credential_exchange, credential_offer_message

    async def receive_offer(
        self, credential_offer_message: CredentialOffer, connection_id: str
    ):
        """
        Receive a credential offer.

        Args:
            credential_offer: Credential offer to receive
            connection_id: Connection to receive offer on

        Returns:
            The credential_exchange_record

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
        await self.updated_record(credential_exchange)

        return credential_exchange

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

        if credential_exchange_record.credential_request:
            self._logger.warning(
                "create_request called multiple times for credential exchange: %s",
                credential_exchange_record.credential_exchange_id,
            )
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
                credential_offer, credential_definition, did
            )

        credential_request_message = CredentialRequest(
            request=json.dumps(credential_exchange_record.credential_request)
        )
        credential_request_message._thread = {
            "thid": credential_exchange_record.thread_id
        }

        credential_exchange_record.state = CredentialExchange.STATE_REQUEST_SENT
        await credential_exchange_record.save(self.context)
        await self.updated_record(credential_exchange_record)

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
        await self.updated_record(credential_exchange_record)

        return credential_exchange_record

    async def issue_credential(self, credential_exchange_record: CredentialExchange):
        """
        Issue a credential.

        Args:
            credential_exchange_record: The credential exchange we are issuing a
                credential for

        Returns:
            Tuple: (Updated credential exchange record, credential message obj)

        """

        schema_id = credential_exchange_record.schema_id

        if credential_exchange_record.credential:
            self._logger.warning(
                "issue_credential called multiple times for credential exchange: %s",
                credential_exchange_record.credential_exchange_id,
            )
        else:
            credential_offer = credential_exchange_record.credential_offer
            credential_request = credential_exchange_record.credential_request
            credential_values = credential_exchange_record.credential_values

            ledger: BaseLedger = await self.context.inject(BaseLedger)
            async with ledger:
                schema = await ledger.get_schema(schema_id)

            issuer: BaseIssuer = await self.context.inject(BaseIssuer)
            (
                credential_exchange_record.credential,
                credential_revocation_id,
            ) = await issuer.create_credential(
                schema, credential_offer, credential_request, credential_values
            )

        credential_exchange_record.state = CredentialExchange.STATE_ISSUED
        await credential_exchange_record.save(self.context)
        await self.updated_record(credential_exchange_record)

        credential_message = CredentialIssue(
            issue=json.dumps(credential_exchange_record.credential)
        )
        credential_message._thread = {
            "thid": credential_exchange_record.thread_id,
            "pthid": credential_exchange_record.parent_thread_id,
        }

        return credential_exchange_record, credential_message

    async def store_credential(self, credential_message: CredentialIssue):
        """
        Store a credential in the wallet.

        Args:
            credential_message: credential to store

        """
        credential = json.loads(credential_message.issue)

        try:
            (
                credential_exchange_record
            ) = await CredentialExchange.retrieve_by_tag_filter(
                self.context, tag_filter={"thread_id": credential_message._thread_id}
            )
        except StorageNotFoundError:

            if not credential_message._thread or not credential_message._thread.pthid:
                raise

            # If the thread_id does not return any results, we check the
            # parent thread id to see if this exchange is nested and is
            # re-using information from parent. In this case, we need the parent
            # exchange state object to retrieve and re-use the
            # credential_request_metadata
            (
                credential_exchange_record
            ) = await CredentialExchange.retrieve_by_tag_filter(
                self.context, tag_filter={"thread_id": credential_message._thread.pthid}
            )

            credential_exchange_record._id = None
            credential_exchange_record.thread_id = credential_message._thread_id
            credential_exchange_record.credential_id = None
            credential_exchange_record.credential = None

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

        credential_exchange_record.state = CredentialExchange.STATE_STORED
        credential_exchange_record.credential_id = credential_id
        credential_exchange_record.credential = wallet_credential
        await credential_exchange_record.save(self.context)
        await self.updated_record(credential_exchange_record)

    async def updated_record(self, credential_exchange: CredentialExchange):
        """Call webhook when the record is updated."""
        responder = await self._context.inject(BaseResponder, required=False)
        if responder:
            await responder.send_webhook("credentials", credential_exchange.serialize())
