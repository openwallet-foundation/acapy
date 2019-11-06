"""Classes to manage presentations."""

import json
import logging
from uuid import uuid4

from ...config.injection_context import InjectionContext
from ...error import BaseError
from ...holder.base import BaseHolder
from ...ledger.base import BaseLedger
from ...verifier.base import BaseVerifier

from .models.presentation_exchange import PresentationExchange
from .messages.presentation_request import PresentationRequest
from .messages.credential_presentation import CredentialPresentation


class PresentationManagerError(BaseError):
    """Presentation error."""


class PresentationManager:
    """Class for managing presentations."""

    def __init__(self, context: InjectionContext):
        """
        Initialize a PresentationManager.

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
            The injection context for this presentation manager

        """
        return self._context

    async def create_request(
        self,
        name: str,
        version: str,
        requested_attributes: list,
        requested_predicates: list,
        connection_id: str,
    ):
        """Create a proof request."""

        presentation_request = {
            "name": name,
            "version": version,
            "nonce": str(uuid4().int),
            "requested_attributes": {},
            "requested_predicates": {},
        }

        for requested_attribute in requested_attributes:
            presentation_request["requested_attributes"][
                str(uuid4())
            ] = requested_attribute

        for requested_predicates in requested_predicates:
            presentation_request["requested_predicates"][
                str(uuid4())
            ] = requested_predicates

        presentation_request_message = PresentationRequest(
            request=json.dumps(presentation_request)
        )

        presentation_exchange = PresentationExchange(
            connection_id=connection_id,
            initiator=PresentationExchange.INITIATOR_SELF,
            state=PresentationExchange.STATE_REQUEST_SENT,
            presentation_request=presentation_request,
            thread_id=presentation_request_message._thread_id,
        )

        await presentation_exchange.save(
            self.context, reason="Create presentation request"
        )

        return presentation_exchange, presentation_request_message

    async def receive_request(
        self, presentation_request_message: PresentationRequest, connection_id: str
    ):
        """
        Receive a presentation request.

        Args:
            presentation_request_message: Presentation message to receive
        """

        presentation_exchange = PresentationExchange(
            connection_id=connection_id,
            thread_id=presentation_request_message._thread_id,
            initiator=PresentationExchange.INITIATOR_EXTERNAL,
            state=PresentationExchange.STATE_REQUEST_RECEIVED,
            presentation_request=json.loads(presentation_request_message.request),
        )

        await presentation_exchange.save(
            self.context, reason="Receive presentation request"
        )

        return presentation_exchange

    async def create_presentation(
        self,
        presentation_exchange_record: PresentationExchange,
        requested_credentials: dict,
    ):
        """
        Receive a presentation request.

        Args:
            presentation_exchange_record: Record to update
            requested_credentials: Indy formatted requested_credentials

        i.e.,

        ::

            {
                "self_attested_attributes": {
                    "j233ffbc-bd35-49b1-934f-51e083106f6d": "value"
                },
                "requested_attributes": {
                    "6253ffbb-bd35-49b3-934f-46e083106f6c": {
                        "cred_id": "5bfa40b7-062b-4ae0-a251-a86c87922c0e",
                        "revealed": true
                    }
                },
                "requested_predicates": {
                    "bfc8a97d-60d3-4f21-b998-85eeabe5c8c0": {
                        "cred_id": "5bfa40b7-062b-4ae0-a251-a86c87922c0e"
                    }
                }
            }

        """

        # Get all credential ids for this presentation
        credential_ids = []

        requested_attributes = requested_credentials["requested_attributes"]
        for presentation_referent in requested_attributes:
            credential_id = requested_attributes[presentation_referent]["cred_id"]
            credential_ids.append(credential_id)

        requested_predicates = requested_credentials["requested_predicates"]
        for presentation_referent in requested_predicates:
            credential_id = requested_predicates[presentation_referent]["cred_id"]
            credential_ids.append(credential_id)

        # Get all schema and credential definition ids in use
        # TODO: Cache this!!!
        schema_ids = []
        credential_definition_ids = []
        holder: BaseHolder = await self.context.inject(BaseHolder)
        for credential_id in credential_ids:
            credential = await holder.get_credential(credential_id)
            schema_id = credential["schema_id"]
            credential_definition_id = credential["cred_def_id"]
            schema_ids.append(schema_id)
            credential_definition_ids.append(credential_definition_id)

        schemas = {}
        credential_definitions = {}

        ledger: BaseLedger = await self.context.inject(BaseLedger)
        async with ledger:

            # Build schemas for anoncreds
            for schema_id in schema_ids:
                schema = await ledger.get_schema(schema_id)
                schemas[schema_id] = schema

            # Build credential_definitions for anoncreds
            for credential_definition_id in credential_definition_ids:
                (credential_definition) = await ledger.get_credential_definition(
                    credential_definition_id
                )
                credential_definitions[credential_definition_id] = credential_definition

        holder: BaseHolder = await self.context.inject(BaseHolder)
        presentation = await holder.create_presentation(
            presentation_exchange_record.presentation_request,
            requested_credentials,
            schemas,
            credential_definitions,
        )

        presentation_message = CredentialPresentation(
            presentation=json.dumps(presentation)
        )

        # TODO: Find a more elegant way to do this
        presentation_message._thread = {"thid": presentation_exchange_record.thread_id}

        # save presentation exchange state
        presentation_exchange_record.state = (
            PresentationExchange.STATE_PRESENTATION_SENT
        )
        presentation_exchange_record.presentation = presentation
        await presentation_exchange_record.save(
            self.context,
            reason="Create presentation",
            log_params={"requested_credentials": requested_credentials},
        )

        return presentation_exchange_record, presentation_message

    async def receive_presentation(self, presentation: dict, thread_id: str):
        """Receive a presentation request."""
        (
            presentation_exchange_record
        ) = await PresentationExchange.retrieve_by_tag_filter(
            self.context, {"thread_id": thread_id}, {"initiator": "self"}
        )

        presentation_exchange_record.presentation = presentation
        presentation_exchange_record.state = (
            PresentationExchange.STATE_PRESENTATION_RECEIVED
        )
        await presentation_exchange_record.save(
            self.context, reason="Receive presentation"
        )

        return presentation_exchange_record

    async def verify_presentation(
        self, presentation_exchange_record: PresentationExchange
    ):
        """Verify a presentation request."""

        presentation_request = presentation_exchange_record.presentation_request
        presentation = presentation_exchange_record.presentation

        schema_ids = []
        credential_definition_ids = []

        identifiers = presentation["identifiers"]
        for identifier in identifiers:
            schema_ids.append(identifier["schema_id"])
            credential_definition_ids.append(identifier["cred_def_id"])

        schemas = {}
        credential_definitions = {}

        ledger: BaseLedger = await self.context.inject(BaseLedger)
        async with ledger:

            # Build schemas for anoncreds
            for schema_id in schema_ids:
                schema = await ledger.get_schema(schema_id)
                schemas[schema_id] = schema

            # Build credential_definitions for anoncreds
            for credential_definition_id in credential_definition_ids:
                (credential_definition) = await ledger.get_credential_definition(
                    credential_definition_id
                )
                credential_definitions[credential_definition_id] = credential_definition

        verifier: BaseVerifier = await self.context.inject(BaseVerifier)
        verified = await verifier.verify_presentation(
            presentation_request, presentation, schemas, credential_definitions
        )

        presentation_exchange_record.verified = "true" if verified else "false"
        presentation_exchange_record.state = PresentationExchange.STATE_VERIFIED

        await presentation_exchange_record.save(
            self.context, reason="Verify presentation"
        )

        return presentation_exchange_record
