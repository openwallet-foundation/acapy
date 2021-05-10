"""V2.0 present-proof dif presentation-exchange format handler."""

import logging

from marshmallow import RAISE
from typing import Mapping, Tuple
from uuid import uuid4

from ......messaging.decorators.attach_decorator import AttachDecorator
from ......storage.error import StorageNotFoundError
from ......storage.vc_holder.base import VCHolder

from ....dif.pres_exch import PresentationDefinition
from ....dif.pres_exch_handler import DIFPresExchHandler
from ....dif.pres_proposal_schema import DIFPresProposalSchema
from ....dif.pres_request_schema import DIFPresRequestSchema
from ....dif.pres_schema import DIFPresSpecSchema
from ......vc.ld_proofs import (
    DocumentLoader,
    Ed25519Signature2018,
    BbsBlsSignature2020,
    BbsBlsSignatureProof2020,
    WalletKeyPair,
)
from ......vc.vc_ld.verify import verify_presentation
from ......wallet.base import BaseWallet
from ......wallet.key_type import KeyType

from ...message_types import (
    PRES_20_REQUEST,
    PRES_20,
    PRES_20_PROPOSAL,
)
from ...messages.pres_format import V20PresFormat
from ...messages.pres_proposal import V20PresProposal
from ...messages.pres_request import V20PresRequest
from ...messages.pres import V20Pres
from ...models.pres_exchange import V20PresExRecord

from ..handler import V20PresFormatHandler, V20PresFormatError

LOGGER = logging.getLogger(__name__)


class DIFPresFormatHandler(V20PresFormatHandler):
    """DIF presentation format handler."""

    format = V20PresFormat.Format.DIF

    ISSUE_SIGNATURE_SUITE_KEY_TYPE_MAPPING = {
        Ed25519Signature2018: KeyType.ED25519,
        BbsBlsSignature2020: KeyType.BLS12381G2,
        BbsBlsSignatureProof2020: KeyType.BLS12381G2,
    }

    async def _get_all_suites(self, wallet: BaseWallet):
        """Get all supported suites for verifying presentation."""
        suites = []
        for suite, key_type in self.ISSUE_SIGNATURE_SUITE_KEY_TYPE_MAPPING.items():
            suites.append(
                suite(
                    key_pair=WalletKeyPair(wallet=wallet, key_type=key_type),
                )
            )
        return suites

    @classmethod
    def validate_fields(cls, message_type: str, attachment_data: Mapping):
        """Validate attachment data for a specific message type.

        Uses marshmallow schemas to validate if format specific attachment data
        is valid for the specified message type. Only does structural and type
        checks, does not validate if .e.g. the issuer value is valid.


        Args:
            message_type (str): The message type to validate the attachment data for.
                Should be one of the message types as defined in message_types.py
            attachment_data (Mapping): [description]
                The attachment data to valide

        Raises:
            Exception: When the data is not valid.

        """
        mapping = {
            PRES_20_REQUEST: DIFPresRequestSchema,
            PRES_20_PROPOSAL: DIFPresProposalSchema,
            PRES_20: DIFPresSpecSchema,
        }

        # Get schema class
        Schema = mapping[message_type]

        # Validate, throw if not valid
        Schema(unknown=RAISE).load(attachment_data)

    async def create_exchange_for_proposal(
        self,
        pres_ex_record: V20PresExRecord,
        pres_proposal_message: V20PresProposal,
    ) -> None:
        """Create a presentation exchange record for input presentation proposal."""

    async def receive_pres_proposal(
        self,
        pres_ex_record: V20PresExRecord,
        message: V20PresProposal,
    ) -> None:
        """Receive a presentation proposal from message in context on manager creation."""

    async def create_exchange_for_request(
        self,
        pres_ex_record: V20PresExRecord,
        pres_request_message: V20PresRequest,
    ) -> None:
        """Create a presentation exchange record for input presentation request."""

    async def create_bound_request(
        self,
        pres_ex_record: V20PresExRecord,
        request_data: dict = None,
    ) -> Tuple[V20PresFormat, AttachDecorator]:
        """
        Create a presentation request bound to a proposal.

        Args:
            pres_ex_record: Presentation exchange record for which
                to create presentation request
            name: name to use in presentation request (None for default)
            version: version to use in presentation request (None for default)
            nonce: nonce to use in presentation request (None to generate)
            comment: Optional human-readable comment pertaining to request creation

        Returns:
            A tuple (updated presentation exchange record, presentation request message)

        """
        dif_proof_request = V20PresProposal.deserialize(
            pres_ex_record.pres_proposal
        ).attachment(self.format)

        return self.get_format_data(PRES_20_REQUEST, dif_proof_request)

    async def create_pres(
        self,
        pres_ex_record: V20PresExRecord,
        request_data: dict = {},
    ) -> Tuple[V20PresFormat, AttachDecorator]:
        """Create a presentation."""
        proof_request = V20PresRequest.deserialize(
            pres_ex_record.pres_request
        ).attachment(self.format)
        pres_definition = None

        if request_data != {}:
            pres_spec_payload = DIFPresRequestSchema().load(request_data)
            # Overriding with prover provided pres_spec
            challenge = str(uuid4())
            domain = None
            pres_definition = pres_spec_payload.get("presentation_definition")
            issuer_id = pres_spec_payload.get("issuer_id")

        if not pres_definition:
            challenge = proof_request.get("challenge") or str(uuid4())
            domain = proof_request.get("domain") or None
            pres_definition = PresentationDefinition.deserialize(
                proof_request.get("presentation_definition")
            )
            issuer_id = None

        input_descriptors = pres_definition.input_descriptors
        try:
            holder = self._profile.inject(VCHolder)
            types = []
            schema_ids = []
            for input_descriptor in input_descriptors:
                for schema in input_descriptor.schemas:
                    uri = schema.uri
                    required = schema.required or True
                    if required:
                        # JSONLD Expanded URLs
                        if "#" in uri:
                            types.append(uri.split("#")[1])
                        else:
                            schema_ids.append(uri)
            if len(types) == 0:
                types = None
            if len(schema_ids) == 0:
                schema_ids = None
            search = holder.search_credentials(
                types=types,
                schema_ids=schema_ids,
            )
            # Defaults to page_size but would like to include all
            # For now, setting to 1000
            max_results = 1000
            records = await search.fetch(max_results)
        except StorageNotFoundError as err:
            raise V20PresFormatError(err)
        # Selecting suite from claim_format
        claim_format = pres_definition.fmt
        proof_type = None
        if claim_format:
            if claim_format.ldp_vp:
                for proof_req in claim_format.ldp_vp.get("proof_type"):
                    if proof_req == "BbsBlsSignature2020":
                        proof_type = "BbsBlsSignature2020"
                        break
                    elif proof_req == "Ed25519Signature2018":
                        proof_type = "Ed25519Signature2018"
                        break

        dif_handler = DIFPresExchHandler(
            self._profile, pres_signing_did=issuer_id, proof_type=proof_type
        )

        pres = await dif_handler.create_vp(
            challenge=challenge,
            domain=domain,
            pd=pres_definition,
            credentials=records,
        )
        return self.get_format_data(PRES_20, pres)

    async def receive_pres(
        self, message: V20Pres, pres_ex_record: V20PresExRecord
    ) -> None:
        """Receive a presentation, from message in context on manager creation."""

    async def verify_pres(self, pres_ex_record: V20PresExRecord) -> V20PresExRecord:
        """
        Verify a presentation.

        Args:
            pres_ex_record: presentation exchange record
                with presentation request and presentation to verify

        Returns:
            presentation exchange record, updated

        """
        async with self._profile.session() as session:
            wallet = session.inject(BaseWallet)
            dif_proof = V20Pres.deserialize(pres_ex_record.pres).attachment(self.format)
            # challenge
            challenge = None
            req_pres_attach = pres_ex_record.pres_request.get(
                "request_presentations~attach"
            )
            for pres_req in req_pres_attach:
                if pres_req.get("@id") == "dif":
                    challenge = pres_req.get("data").get("json").get("challenge")
                    break
            if not challenge:
                raise V20PresFormatError(
                    "No challenge is set for the presentation request"
                )
            pres_ver_result = await verify_presentation(
                presentation=dif_proof,
                suites=await self._get_all_suites(wallet=wallet),
                document_loader=self._profile.inject(DocumentLoader),
                challenge=challenge,
            )
            pres_ex_record.verified = pres_ver_result.verified
            return pres_ex_record
