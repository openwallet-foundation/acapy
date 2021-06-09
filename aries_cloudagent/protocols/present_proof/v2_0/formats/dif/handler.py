"""V2.0 present-proof dif presentation-exchange format handler."""

import logging

from marshmallow import RAISE
from typing import Mapping, Tuple, Sequence
from uuid import uuid4

from ......messaging.decorators.attach_decorator import AttachDecorator
from ......storage.error import StorageNotFoundError
from ......storage.vc_holder.base import VCHolder
from ......storage.vc_holder.vc_record import VCRecord
from ......vc.ld_proofs import (
    DocumentLoader,
    Ed25519Signature2018,
    BbsBlsSignature2020,
    BbsBlsSignatureProof2020,
    WalletKeyPair,
)
from ......vc.ld_proofs.constants import EXPANDED_TYPE_CREDENTIALS_CONTEXT_V1_VC_TYPE
from ......vc.vc_ld.verify import verify_presentation
from ......wallet.base import BaseWallet
from ......wallet.key_type import KeyType

from ....dif.pres_exch import PresentationDefinition
from ....dif.pres_exch_handler import DIFPresExchHandler
from ....dif.pres_proposal_schema import DIFProofProposalSchema
from ....dif.pres_request_schema import (
    DIFProofRequestSchema,
    DIFPresSpecSchema,
)
from ....dif.pres_schema import DIFProofSchema

from ...message_types import (
    ATTACHMENT_FORMAT,
    PRES_20_REQUEST,
    PRES_20,
    PRES_20_PROPOSAL,
)
from ...messages.pres_format import V20PresFormat
from ...messages.pres import V20Pres
from ...models.pres_exchange import V20PresExRecord

from ..handler import V20PresFormatHandler, V20PresFormatHandlerError

LOGGER = logging.getLogger(__name__)


class DIFPresFormatHandler(V20PresFormatHandler):
    """DIF presentation format handler."""

    format = V20PresFormat.Format.DIF

    ISSUE_SIGNATURE_SUITE_KEY_TYPE_MAPPING = {
        Ed25519Signature2018: KeyType.ED25519,
    }

    if BbsBlsSignature2020.BBS_SUPPORTED:
        ISSUE_SIGNATURE_SUITE_KEY_TYPE_MAPPING[BbsBlsSignature2020] = KeyType.BLS12381G2
        ISSUE_SIGNATURE_SUITE_KEY_TYPE_MAPPING[
            BbsBlsSignatureProof2020
        ] = KeyType.BLS12381G2

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
            PRES_20_REQUEST: DIFProofRequestSchema,
            PRES_20_PROPOSAL: DIFProofProposalSchema,
            PRES_20: DIFProofSchema,
        }

        # Get schema class
        Schema = mapping[message_type]

        # Validate, throw if not valid
        Schema(unknown=RAISE).load(attachment_data)

    def get_format_identifier(self, message_type: str) -> str:
        """Get attachment format identifier for format and message combination.

        Args:
            message_type (str): Message type for which to return the format identifier

        Returns:
            str: Issue credential attachment format identifier

        """
        return ATTACHMENT_FORMAT[message_type][DIFPresFormatHandler.format.api]

    def get_format_data(
        self, message_type: str, data: dict
    ) -> Tuple[V20PresFormat, AttachDecorator]:
        """Get presentation format and attach objects for use in pres_ex messages."""

        return (
            V20PresFormat(
                attach_id=DIFPresFormatHandler.format.api,
                format_=self.get_format_identifier(message_type),
            ),
            AttachDecorator.data_json(data, ident=DIFPresFormatHandler.format.api),
        )

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
        dif_proof_request = pres_ex_record.pres_proposal.attachment(
            DIFPresFormatHandler.format
        )

        return self.get_format_data(PRES_20_REQUEST, dif_proof_request)

    async def create_pres(
        self,
        pres_ex_record: V20PresExRecord,
        request_data: dict = {},
    ) -> Tuple[V20PresFormat, AttachDecorator]:
        """Create a presentation."""
        proof_request = pres_ex_record.pres_request.attachment(
            DIFPresFormatHandler.format
        )
        pres_definition = None
        limit_record_ids = None
        challenge = None
        domain = None
        if request_data != {} and DIFPresFormatHandler.format.api in request_data:
            dif_spec = request_data.get(DIFPresFormatHandler.format.api)
            pres_spec_payload = DIFPresSpecSchema().load(dif_spec)
            # Overriding with prover provided pres_spec
            pres_definition = pres_spec_payload.get("presentation_definition")
            issuer_id = pres_spec_payload.get("issuer_id")
            limit_record_ids = pres_spec_payload.get("record_ids")
        if not pres_definition:
            if "options" in proof_request:
                challenge = proof_request.get("options").get("challenge")
                domain = proof_request.get("options").get("domain")
            pres_definition = PresentationDefinition.deserialize(
                proof_request.get("presentation_definition")
            )
            issuer_id = None
        if not challenge:
            challenge = str(uuid4())

        input_descriptors = pres_definition.input_descriptors
        try:
            holder = self._profile.inject(VCHolder)
            record_ids = set()
            credentials_list = []
            if not limit_record_ids:
                for input_descriptor in input_descriptors:
                    expanded_types = set()
                    schema_ids = set()
                    for schema in input_descriptor.schemas:
                        uri = schema.uri
                        required = schema.required or True
                        if required:
                            # JSONLD Expanded URLs
                            if "#" in uri:
                                expanded_types.add(uri)
                            else:
                                schema_ids.add(uri)
                    if len(schema_ids) == 0:
                        schema_ids_list = None
                    else:
                        schema_ids_list = list(schema_ids)
                    if len(expanded_types) == 0:
                        expanded_types_list = None
                    else:
                        expanded_types_list = list(expanded_types)
                        # Raise Exception if expanded type extracted from
                        # CREDENTIALS_CONTEXT_V1_URL and
                        # VERIFIABLE_CREDENTIAL_TYPE is the only schema.uri
                        # specified in the presentation_definition.
                        if len(expanded_types_list) == 1:
                            if expanded_types_list[0] in [
                                EXPANDED_TYPE_CREDENTIALS_CONTEXT_V1_VC_TYPE
                            ]:
                                raise V20PresFormatHandlerError(
                                    "Only expanded type extracted from "
                                    "CREDENTIALS_CONTEXT_V1_URL and "
                                    "VERIFIABLE_CREDENTIAL_TYPE included "
                                    "as the schema.uri"
                                )
                    search = holder.search_credentials(
                        types=expanded_types_list,
                        schema_ids=schema_ids_list,
                    )
                    # Defaults to page_size but would like to include all
                    # For now, setting to 1000
                    max_results = 1000
                    records = await search.fetch(max_results)
                    # Avoiding addition of duplicate records
                    (
                        vcrecord_list,
                        vcrecord_ids_set,
                    ) = await self.process_vcrecords_return_list(records, record_ids)
                    record_ids = vcrecord_ids_set
                    credentials_list = credentials_list + vcrecord_list
            else:
                records = []
                for record_id in limit_record_ids:
                    records.append(await holder.retrieve_credential_by_id(record_id))
                # Avoiding addition of duplicate records
                (
                    vcrecord_list,
                    vcrecord_ids_set,
                ) = await self.process_vcrecords_return_list(records, record_ids)
                record_ids = vcrecord_ids_set
                credentials_list = credentials_list + vcrecord_list
        except StorageNotFoundError as err:
            raise V20PresFormatHandlerError(err)
        # Selecting suite from claim_format
        claim_format = pres_definition.fmt
        proof_type = None
        if claim_format:
            if claim_format.ldp_vp:
                for proof_req in claim_format.ldp_vp.get("proof_type"):
                    if proof_req == Ed25519Signature2018.signature_type:
                        proof_type = Ed25519Signature2018.signature_type
                        break
                    elif proof_req == BbsBlsSignature2020.signature_type:
                        proof_type = BbsBlsSignature2020.signature_type
                        break

        dif_handler = DIFPresExchHandler(
            self._profile, pres_signing_did=issuer_id, proof_type=proof_type
        )

        pres = await dif_handler.create_vp(
            challenge=challenge,
            domain=domain,
            pd=pres_definition,
            credentials=credentials_list,
        )
        return self.get_format_data(PRES_20, pres)

    async def process_vcrecords_return_list(
        self, vc_records: Sequence[VCRecord], record_ids: set
    ) -> Tuple[Sequence[VCRecord], set]:
        """Return list of non-duplicate VCRecords."""
        to_add = []
        for vc_record in vc_records:
            if vc_record.record_id not in record_ids:
                to_add.append(vc_record)
                record_ids.add(vc_record.record_id)
        return (to_add, record_ids)

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
            dif_proof = pres_ex_record.pres.attachment(DIFPresFormatHandler.format)
            pres_request = pres_ex_record.pres_request.attachment(
                DIFPresFormatHandler.format
            )
            if "options" in pres_request:
                challenge = pres_request.get("options").get("challenge")
            else:
                raise V20PresFormatHandlerError(
                    "No options [challenge] set for the presentation request"
                )
            if not challenge:
                raise V20PresFormatHandlerError(
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
