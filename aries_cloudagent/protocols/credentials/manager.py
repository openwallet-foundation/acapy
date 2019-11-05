"""Classes to manage credentials."""

import json
import logging

from ...config.injection_context import InjectionContext
from ...connections.models.connection_record import ConnectionRecord
from ...error import BaseError
from ...holder.base import BaseHolder
from ...issuer.base import BaseIssuer
from ...ledger.base import BaseLedger

from .messages.credential_issue import CredentialIssue
from .messages.credential_stored import CredentialStored
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

        cache_key = f"credential_offer::{credential_definition_id}"
        cached = await CredentialExchange.get_cached_key(self.context, cache_key)
        if cached:
            credential_offer = cached["offer"]
        else:
            issuer: BaseIssuer = await self.context.inject(BaseIssuer)
            credential_offer = await issuer.create_credential_offer(
                credential_definition_id
            )
            await CredentialExchange.set_cached_key(
                self.context, cache_key, {"offer": credential_offer}, 3600
            )

        credential_offer_message = CredentialOffer(
            offer_json=json.dumps(credential_offer)
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
            thread_id=credential_offer_message._thread_id,
        )
        await credential_exchange.save(self.context, reason="Create credential offer")
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
        await credential_exchange.save(self.context, reason="Receive credential offer")

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
            nonce = credential_offer["nonce"]
            cache_key = (
                f"credential_request::{credential_definition_id}::{did}::{nonce}"
            )
            cached = await CredentialExchange.get_cached_key(self.context, cache_key)
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
                    credential_offer, credential_definition, did
                )
                await CredentialExchange.set_cached_key(
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
            request=json.dumps(credential_exchange_record.credential_request)
        )

        credential_request_message.assign_thread_id(
            credential_exchange_record.thread_id
        )

        credential_exchange_record.state = CredentialExchange.STATE_REQUEST_SENT
        await credential_exchange_record.save(
            self.context, reason="Create credential request"
        )

        return credential_exchange_record, credential_request_message

    async def receive_request(self, credential_request_message: CredentialRequest):
        """
        Receive a credential request.

        Args:
            credential_request_message: Credential request to receive

        """

        credential_request = json.loads(credential_request_message.request)

        (
            credential_exchange_record
        ) = await CredentialExchange.retrieve_by_thread_and_initiator(
            self.context, credential_request_message._thread_id, "self"
        )
        credential_exchange_record.credential_request = credential_request
        credential_exchange_record.state = CredentialExchange.STATE_REQUEST_RECEIVED
        await credential_exchange_record.save(
            self.context, reason="Receive credential request"
        )

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
                _,  # credential_revocation_id
            ) = await issuer.create_credential(
                schema, credential_offer, credential_request, credential_values
            )

        credential_exchange_record.state = CredentialExchange.STATE_ISSUED

        credential_message = CredentialIssue(
            issue=json.dumps(credential_exchange_record.credential)
        )

        if credential_exchange_record.thread_id:
            credential_message.assign_thread_id(
                thid=credential_exchange_record.thread_id
            )
        else:
            raise CredentialManagerError(
                "The credential exchange object must have a "
                + "thread id in order to issue a credential."
            )

        await credential_exchange_record.save(self.context, reason="Issue credential")
        return credential_exchange_record, credential_message

    async def receive_credential(self, credential_message: CredentialIssue):
        """
        Receive a credential a credential from an issuer.

        Hold in storage to be potentially processed by controller before storing.

        Args:
            credential_message: credential to store

        """
        raw_credential = json.loads(credential_message.issue)

        (
            credential_exchange_record
        ) = await CredentialExchange.retrieve_by_thread_and_initiator(
            self.context, credential_message._thread_id, "external"
        )

        credential_exchange_record.raw_credential = raw_credential
        credential_exchange_record.state = CredentialExchange.STATE_CREDENTIAL_RECEIVED

        await credential_exchange_record.save(self.context, reason="Receive credential")

        return credential_exchange_record

    async def store_credential(
        self, credential_exchange_record: CredentialExchange, credential_id: str = None
    ):
        """
        Store a credential in the wallet.

        Args:
            credential_message: credential to store
            credential_id: string to use as id for record in wallet

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
            credential_id=credential_id,
        )

        credential = await holder.get_credential(credential_id)

        credential_exchange_record.state = CredentialExchange.STATE_STORED
        credential_exchange_record.credential_id = credential_id
        credential_exchange_record.credential = credential

        await credential_exchange_record.save(self.context, reason="Store credential")

        credential_stored_message = CredentialStored()
        credential_stored_message.assign_thread_id(credential_exchange_record.thread_id)

        # We're done so delete the exchange record
        await credential_exchange_record.delete_record(self.context)

        return credential_exchange_record, credential_stored_message

    async def credential_stored(self, credential_stored_message: CredentialStored):
        """
        Receive confirmation that holder stored credential.

        Args:
            credential_message: credential to store

        """

        # Get current exchange record by thread id
        (
            credential_exchange_record
        ) = await CredentialExchange.retrieve_by_thread_and_initiator(
            self.context, credential_stored_message._thread_id, "self"
        )

        credential_exchange_record.state = CredentialExchange.STATE_STORED
        await credential_exchange_record.save(self.context, reason="Credential stored")

        # We're done so delete the exchange record
        await credential_exchange_record.delete_record(self.context)
