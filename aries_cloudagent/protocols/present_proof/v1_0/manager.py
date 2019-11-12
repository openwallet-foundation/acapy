"""Classes to manage presentations."""

import json
import logging

from ....config.injection_context import InjectionContext
from ....error import BaseError
from ....holder.base import BaseHolder
from ....ledger.base import BaseLedger
from ....messaging.decorators.attach_decorator import AttachDecorator
from ....messaging.responder import BaseResponder
from ....verifier.base import BaseVerifier

from .models.presentation_exchange import V10PresentationExchange
from .messages.presentation_ack import PresentationAck
from .messages.presentation_proposal import PresentationProposal
from .messages.presentation_request import PresentationRequest
from .messages.presentation import Presentation
from .message_types import ATTACH_DECO_IDS, PRESENTATION, PRESENTATION_REQUEST


class PresentationManagerError(BaseError):
    """Presentation error."""


class PresentationManager:
    """Class for managing presentations."""

    def __init__(self, context: InjectionContext):
        """
        Initialize a PresentationManager.

        Args:
            context: The context for this presentation
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

    async def create_exchange_for_proposal(
        self,
        connection_id: str,
        presentation_proposal_message: PresentationProposal,
        auto_present: bool = None,
    ):
        """
        Create a presentation exchange record for input presentation proposal.

        Args:
            connection_id: connection identifier
            presentation_proposal_message: presentation proposal to serialize
                to exchange record
            auto_present: whether to present proof upon receiving proof request
                (default to configuration setting)

        Returns:
            Presentation exchange record, created

        """
        presentation_exchange_record = V10PresentationExchange(
            connection_id=connection_id,
            thread_id=presentation_proposal_message._thread_id,
            initiator=V10PresentationExchange.INITIATOR_SELF,
            role=V10PresentationExchange.ROLE_PROVER,
            state=V10PresentationExchange.STATE_PROPOSAL_SENT,
            presentation_proposal_dict=presentation_proposal_message.serialize(),
            auto_present=auto_present,
        )
        await presentation_exchange_record.save(
            self.context, reason="create presentation proposal"
        )

        return presentation_exchange_record

    async def receive_proposal(self):
        """
        Receive a presentation proposal from message in context on manager creation.

        Returns:
            Presentation exchange record, created

        """
        presentation_proposal_message = self.context.message
        presentation_exchange_record = V10PresentationExchange(
            connection_id=self.context.connection_record.connection_id,
            thread_id=presentation_proposal_message._thread_id,
            initiator=V10PresentationExchange.INITIATOR_EXTERNAL,
            role=V10PresentationExchange.ROLE_VERIFIER,
            state=V10PresentationExchange.STATE_PROPOSAL_RECEIVED,
            presentation_proposal_dict=presentation_proposal_message.serialize(),
        )
        await presentation_exchange_record.save(
            self.context, reason="receive presentation request"
        )

        return presentation_exchange_record

    async def create_bound_request(
        self,
        presentation_exchange_record: V10PresentationExchange,
        name: str = None,
        version: str = None,
        nonce: str = None,
        comment: str = None,
    ):
        """
        Create a presentation request bound to a proposal.

        Args:
            presentation_exchange_record: Presentation exchange record for which
                to create presentation request
            name: name to use in presentation request (None for default)
            version: version to use in presentation request (None for default)
            nonce: nonce to use in presentation request (None to generate)
            comment: Optional human-readable comment pertaining to request creation

        Returns:
            A tuple (updated presentation exchange record, presentation request message)

        """
        indy_proof_request = await (
            PresentationProposal.deserialize(
                presentation_exchange_record.presentation_proposal_dict
            )
        ).presentation_proposal.indy_proof_request(
            name=name, version=version, nonce=nonce
        )

        presentation_request_message = PresentationRequest(
            comment=comment,
            request_presentations_attach=[
                AttachDecorator.from_indy_dict(
                    indy_dict=indy_proof_request,
                    ident=ATTACH_DECO_IDS[PRESENTATION_REQUEST],
                )
            ],
        )
        presentation_request_message._thread = {
            "thid": presentation_exchange_record.thread_id
        }

        presentation_exchange_record.thread_id = presentation_request_message._thread_id
        presentation_exchange_record.state = V10PresentationExchange.STATE_REQUEST_SENT
        presentation_exchange_record.presentation_request = indy_proof_request
        await presentation_exchange_record.save(
            self.context, reason="create (bound) presentation request"
        )

        return presentation_exchange_record, presentation_request_message

    async def create_exchange_for_request(
        self, connection_id: str, presentation_request_message: PresentationRequest
    ):
        """
        Create a presentation exchange record for input presentation request.

        Args:
            connection_id: connection identifier
            presentation_request_message: presentation request to use in creating
                exchange record, extracting indy proof request and thread id

        Returns:
            Presentation exchange record, updated

        """
        presentation_exchange_record = V10PresentationExchange(
            connection_id=connection_id,
            thread_id=presentation_request_message._thread_id,
            initiator=V10PresentationExchange.INITIATOR_SELF,
            role=V10PresentationExchange.ROLE_VERIFIER,
            state=V10PresentationExchange.STATE_REQUEST_SENT,
            presentation_request=presentation_request_message.indy_proof_request(),
        )
        await presentation_exchange_record.save(
            self.context, reason="create (free) presentation request"
        )

        return presentation_exchange_record

    async def receive_request(
        self, presentation_exchange_record: V10PresentationExchange
    ):
        """
        Receive a presentation request.

        Args:
            presentation_exchange_record: presentation exchange record with
                request to receive

        Returns:
            The presentation_exchange_record, updated

        """
        presentation_exchange_record.state = (
            V10PresentationExchange.STATE_REQUEST_RECEIVED
        )
        await presentation_exchange_record.save(
            self.context, reason="receive presentation request"
        )

        return presentation_exchange_record

    async def create_presentation(
        self,
        presentation_exchange_record: V10PresentationExchange,
        requested_credentials: dict,
        comment: str = None,
    ):
        """
        Create a presentation.

        Args:
            presentation_exchange_record: Record to update
            requested_credentials: Indy formatted requested_credentials

            e.g.,

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

            comment: optional human-readable comment

        Returns:
            A tuple (updated presentation exchange record, presentation message)

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
        indy_proof = await holder.create_presentation(
            presentation_exchange_record.presentation_request,
            requested_credentials,
            schemas,
            credential_definitions,
        )

        presentation_message = Presentation(
            comment=comment,
            presentations_attach=[
                AttachDecorator.from_indy_dict(
                    indy_dict=indy_proof, ident=ATTACH_DECO_IDS[PRESENTATION]
                )
            ],
        )

        presentation_message._thread = {"thid": presentation_exchange_record.thread_id}

        # save presentation exchange state
        presentation_exchange_record.state = (
            V10PresentationExchange.STATE_PRESENTATION_SENT
        )
        presentation_exchange_record.presentation = indy_proof
        await presentation_exchange_record.save(
            self.context, reason="create presentation"
        )

        return presentation_exchange_record, presentation_message

    async def receive_presentation(self):
        """
        Receive a presentation, from message in context on manager creation.

        Returns:
            presentation exchange record, retrieved and updated

        """
        presentation = self.context.message.indy_proof()
        thread_id = self.context.message._thread_id
        (
            presentation_exchange_record
        ) = await V10PresentationExchange.retrieve_by_tag_filter(
            self.context,
            {"thread_id": thread_id},
            {"connection_id": self.context.connection_record.connection_id},
        )

        presentation_exchange_record.presentation = presentation
        presentation_exchange_record.state = (
            V10PresentationExchange.STATE_PRESENTATION_RECEIVED
        )

        await presentation_exchange_record.save(
            self.context, reason="receive presentation"
        )

        return presentation_exchange_record

    async def verify_presentation(
        self, presentation_exchange_record: V10PresentationExchange
    ):
        """
        Verify a presentation.

        Args:
            presentation_exchange_record: presentation exchange record
                with presentation request and presentation to verify

        Returns:
            presentation record, updated

        """
        indy_proof_request = presentation_exchange_record.presentation_request
        indy_proof = presentation_exchange_record.presentation

        schema_ids = []
        credential_definition_ids = []

        identifiers = indy_proof["identifiers"]
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
        presentation_exchange_record.verified = json.dumps(  # tag: needs string value
            await verifier.verify_presentation(
                indy_proof_request, indy_proof, schemas, credential_definitions
            )
        )
        presentation_exchange_record.state = V10PresentationExchange.STATE_VERIFIED

        await presentation_exchange_record.save(
            self.context, reason="verify presentation"
        )

        await self.send_presentation_ack(presentation_exchange_record)
        return presentation_exchange_record

    async def send_presentation_ack(
        self, presentation_exchange_record: V10PresentationExchange
    ):
        """
        Send acknowledgement of presentation receipt.

        Args:
            presentation_exchange_record: presentation exchange record with thread id

        """
        responder = await self.context.inject(BaseResponder, required=False)

        if responder:
            presentation_ack_message = PresentationAck()
            presentation_ack_message._thread = {
                "thid": presentation_exchange_record.thread_id
            }

            await responder.send_reply(presentation_ack_message)
        else:
            self._logger.warning(
                "Configuration has no BaseResponder: cannot ack presentation on %s",
                presentation_exchange_record.thread_id
            )

    async def receive_presentation_ack(self):
        """
        Receive a presentation ack, from message in context on manager creation.

        Returns:
            presentation exchange record, retrieved and updated

        """
        (
            presentation_exchange_record
        ) = await V10PresentationExchange.retrieve_by_tag_filter(
            self.context,
            tag_filter={
                "thread_id": self.context.message._thread_id,
                "connection_id": self.context.connection_record.connection_id,
            },
        )

        presentation_exchange_record.state = (
            V10PresentationExchange.STATE_PRESENTATION_ACKED
        )

        await presentation_exchange_record.save(
            self.context,
            reason="receive presentation ack",
        )

        return presentation_exchange_record
