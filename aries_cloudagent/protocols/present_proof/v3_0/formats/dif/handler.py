"""V2.0 present-proof dif presentation-exchange format handler."""

import json
import logging

from typing import Mapping, Tuple, Sequence
from uuid import uuid4
from marshmallow import RAISE


from ......messaging.base_handler import BaseResponder
from ......messaging.decorators.attach_decorator_didcomm_v2_pres import AttachDecorator
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
from ......vc.vc_ld.verify import verify_presentation
from ......wallet.base import BaseWallet
from ......wallet.key_type import ED25519, BLS12381G2

from .....problem_report.v1_0.message import ProblemReport

from ....dif.pres_exch import PresentationDefinition, SchemaInputDescriptor
from ....dif.pres_exch_handler import DIFPresExchHandler, DIFPresExchError
from ....dif.pres_proposal_schema import DIFProofProposalSchema
from ....dif.pres_request_schema import (
    DIFProofRequestSchema,
    DIFPresSpecSchema,
)
from ....dif.pres_schema import DIFProofSchema
from ....v2_0.messages.pres_problem_report import ProblemReportReason

from ...message_types import (
    ATTACHMENT_FORMAT,
    PRES_30_REQUEST,
    PRES_30,
    PRES_30_PROPOSAL,
)
from ...messages.pres_format import V30PresFormat
from ...messages.pres import V30Pres
from ...models.pres_exchange import V30PresExRecord

from ..handler import V30PresFormatHandler, V30PresFormatHandlerError

LOGGER = logging.getLogger(__name__)


class DIFPresFormatHandler(V30PresFormatHandler):
    """DIF presentation format handler."""

    format = V30PresFormat.Format.DIF

    ISSUE_SIGNATURE_SUITE_KEY_TYPE_MAPPING = {
        Ed25519Signature2018: ED25519,
    }

    if BbsBlsSignature2020.BBS_SUPPORTED:
        ISSUE_SIGNATURE_SUITE_KEY_TYPE_MAPPING[BbsBlsSignature2020] = BLS12381G2
        ISSUE_SIGNATURE_SUITE_KEY_TYPE_MAPPING[BbsBlsSignatureProof2020] = BLS12381G2

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
            PRES_30_REQUEST: DIFProofRequestSchema,
            PRES_30_PROPOSAL: DIFProofProposalSchema,
            PRES_30: DIFProofSchema,
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
    ) -> Tuple[V30PresFormat, AttachDecorator]:
        """Get presentation format and attach objects for use in pres_ex messages."""

        # TODO: Check if returning 1 format would be ok
        format = V30PresFormat(
            # attach_id=DIFPresFormatHandler.format.api,
            format_=self.get_format_identifier(message_type),
        )
        return (
            format,
            AttachDecorator.data_json(
                data, ident=DIFPresFormatHandler.format.api, format=format
            ),
        )

    async def create_bound_request(
        self,
        pres_ex_record: V30PresExRecord,
        request_data: dict = None,
    ) -> Tuple[V30PresFormat, AttachDecorator]:
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
        dif_proof_request = {}
        pres_proposal_dict_atch = pres_ex_record.pres_proposal.attachments
        for att in pres_proposal_dict_atch:
            if (
                V30PresFormat.Format.get(att.format.format).api
                == V30PresFormat.Format.DIF.api
            ):
                pres_proposal_dict = att.content
        if "options" not in pres_proposal_dict:
            dif_proof_request["options"] = {"challenge": str(uuid4())}
        else:
            dif_proof_request["options"] = pres_proposal_dict["options"]
            del pres_proposal_dict["options"]
            if "challenge" not in dif_proof_request.get("options"):
                dif_proof_request["options"]["challenge"] = str(uuid4())
        dif_proof_request["presentation_definition"] = pres_proposal_dict

        return self.get_format_data(PRES_30_REQUEST, dif_proof_request)

    async def create_pres(
        self,
        pres_ex_record: V30PresExRecord,
        request_data: dict = {},
    ) -> Tuple[V30PresFormat, AttachDecorator]:
        """Create a presentation."""
        proof_request_atch = pres_ex_record.pres_request.attachments
        for att in proof_request_atch:
            if (
                V30PresFormat.Format.get(att.format.format).api
                == V30PresFormat.Format.DIF.api
            ):
                proof_request = att.content
        pres_definition = None
        limit_record_ids = None
        reveal_doc_frame = None
        challenge = None
        domain = None
        if request_data != {} and DIFPresFormatHandler.format.api in request_data:
            dif_spec = request_data.get(DIFPresFormatHandler.format.api)
            pres_spec_payload = DIFPresSpecSchema().load(dif_spec)
            # Overriding with prover provided pres_spec
            pres_definition = pres_spec_payload.get("presentation_definition")
            issuer_id = pres_spec_payload.get("issuer_id")
            limit_record_ids = pres_spec_payload.get("record_ids")
            reveal_doc_frame = pres_spec_payload.get("reveal_doc")
        if not pres_definition:
            if "options" in proof_request:
                challenge = proof_request["options"].get("challenge")
                domain = proof_request["options"].get("domain")
            pres_definition = PresentationDefinition.deserialize(
                proof_request.get("presentation_definition")
            )
            issuer_id = None
        if not challenge:
            challenge = str(uuid4())

        input_descriptors = pres_definition.input_descriptors
        claim_fmt = pres_definition.fmt
        dif_handler_proof_type = None
        try:
            holder = self._profile.inject(VCHolder)
            record_ids = set()
            credentials_list = []
            for input_descriptor in input_descriptors:
                proof_type = None
                limit_disclosure = input_descriptor.constraint.limit_disclosure and (
                    input_descriptor.constraint.limit_disclosure == "required"
                )
                uri_list = []
                one_of_uri_groups = []
                if input_descriptor.schemas:
                    if input_descriptor.schemas.oneof_filter:
                        one_of_uri_groups = (
                            await self.retrieve_uri_list_from_schema_filter(
                                input_descriptor.schemas.uri_groups
                            )
                        )
                    else:
                        schema_uris = input_descriptor.schemas.uri_groups[0]
                        for schema_uri in schema_uris:
                            if schema_uri.required is None:
                                required = True
                            else:
                                required = schema_uri.required
                            if required:
                                uri_list.append(schema_uri.uri)
                if len(uri_list) == 0:
                    uri_list = None
                if len(one_of_uri_groups) == 0:
                    one_of_uri_groups = None
                if limit_disclosure:
                    proof_type = [BbsBlsSignature2020.signature_type]
                    dif_handler_proof_type = BbsBlsSignature2020.signature_type
                if claim_fmt:
                    if claim_fmt.ldp_vp:
                        if "proof_type" in claim_fmt.ldp_vp:
                            proof_types = claim_fmt.ldp_vp.get("proof_type")
                            if limit_disclosure and (
                                BbsBlsSignature2020.signature_type not in proof_types
                            ):
                                raise V30PresFormatHandlerError(
                                    "Verifier submitted presentation request with "
                                    "limit_disclosure [selective disclosure] "
                                    "option but verifier does not support "
                                    "BbsBlsSignature2020 format"
                                )
                            elif (
                                len(proof_types) == 1
                                and (
                                    BbsBlsSignature2020.signature_type
                                    not in proof_types
                                )
                                and (
                                    Ed25519Signature2018.signature_type
                                    not in proof_types
                                )
                            ):
                                raise V30PresFormatHandlerError(
                                    "Only BbsBlsSignature2020 and/or "
                                    "Ed25519Signature2018 signature types "
                                    "are supported"
                                )
                            elif (
                                len(proof_types) >= 2
                                and (
                                    BbsBlsSignature2020.signature_type
                                    not in proof_types
                                )
                                and (
                                    Ed25519Signature2018.signature_type
                                    not in proof_types
                                )
                            ):
                                raise V30PresFormatHandlerError(
                                    "Only BbsBlsSignature2020 and "
                                    "Ed25519Signature2018 signature types "
                                    "are supported"
                                )
                            else:
                                for proof_format in proof_types:
                                    if (
                                        proof_format
                                        == Ed25519Signature2018.signature_type
                                    ):
                                        proof_type = [
                                            Ed25519Signature2018.signature_type
                                        ]
                                        dif_handler_proof_type = (
                                            Ed25519Signature2018.signature_type
                                        )
                                        break
                                    elif (
                                        proof_format
                                        == BbsBlsSignature2020.signature_type
                                    ):
                                        proof_type = [
                                            BbsBlsSignature2020.signature_type
                                        ]
                                        dif_handler_proof_type = (
                                            BbsBlsSignature2020.signature_type
                                        )
                                        break
                    else:
                        raise V30PresFormatHandlerError(
                            "Currently, only ldp_vp with "
                            "BbsBlsSignature2020 and Ed25519Signature2018"
                            " signature types are supported"
                        )
                if one_of_uri_groups:
                    records = []
                    cred_group_record_ids = set()
                    for uri_group in one_of_uri_groups:
                        search = holder.search_credentials(
                            proof_types=proof_type, pd_uri_list=uri_group
                        )
                        max_results = 1000
                        cred_group = await search.fetch(max_results)
                        (
                            cred_group_vcrecord_list,
                            cred_group_vcrecord_ids_set,
                        ) = await self.process_vcrecords_return_list(
                            cred_group, cred_group_record_ids
                        )
                        cred_group_record_ids = cred_group_vcrecord_ids_set
                        records = records + cred_group_vcrecord_list
                else:
                    search = holder.search_credentials(
                        proof_types=proof_type, pd_uri_list=uri_list
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
        except StorageNotFoundError as err:
            raise V30PresFormatHandlerError(err)
        except TypeError as err:
            LOGGER.error(str(err))
            responder = self._profile.inject_or(BaseResponder)
            if responder:
                report = ProblemReport(
                    description={
                        "en": (
                            "Presentation request not properly formatted,"
                            " TypeError raised on Holder agent."
                        ),
                        "code": ProblemReportReason.ABANDONED.value,
                    }
                )
                if pres_ex_record.thread_id:
                    report.assign_thread_id(pres_ex_record.thread_id)
                await responder.send_reply(
                    report, connection_id=pres_ex_record.connection_id
                )
                return

        dif_handler = DIFPresExchHandler(
            self._profile,
            pres_signing_did=issuer_id,
            proof_type=dif_handler_proof_type,
            reveal_doc=reveal_doc_frame,
        )
        try:
            pres = await dif_handler.create_vp(
                challenge=challenge,
                domain=domain,
                pd=pres_definition,
                credentials=credentials_list,
                records_filter=limit_record_ids,
            )
            return self.get_format_data(PRES_30, pres)
        except DIFPresExchError as err:
            LOGGER.error(str(err))
            responder = self._profile.inject_or(BaseResponder)
            if responder:
                report = ProblemReport(
                    description={
                        "en": str(err),
                        "code": ProblemReportReason.ABANDONED.value,
                    }
                )
                if pres_ex_record.thread_id:
                    report.assign_thread_id(pres_ex_record.thread_id)
                await responder.send_reply(
                    report, connection_id=pres_ex_record.connection_id
                )

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

    async def retrieve_uri_list_from_schema_filter(
        self, schema_uri_groups: Sequence[Sequence[SchemaInputDescriptor]]
    ) -> Sequence[str]:
        """Retrieve list of schema uri from uri_group."""
        group_schema_uri_list = []
        for schema_group in schema_uri_groups:
            uri_list = []
            for schema in schema_group:
                uri_list.append(schema.uri)
            if len(uri_list) > 0:
                group_schema_uri_list.append(uri_list)
        return group_schema_uri_list

    async def receive_pres(self, message: V30Pres, pres_ex_record: V30PresExRecord):
        """Receive a presentation, from message in context on manager creation."""
        dif_handler = DIFPresExchHandler(self._profile)
        dif_proof_atch = message.attachments
        dif_proof = None
        # TODO check if dif_proof it actually contains vals
        for att in dif_proof_atch:
            if (
                V30PresFormat.Format.get(att.format.format).api
                == V30PresFormat.Format.DIF.api
            ):
                dif_proof = att.content
        proof_request_atch = pres_ex_record.pres_request.attachments
        for att in proof_request_atch:
            if (
                V30PresFormat.Format.get(att.format.format).api
                == V30PresFormat.Format.DIF.api
            ):
                proof_request = att.content
        pres_definition = PresentationDefinition.deserialize(
            proof_request.get("presentation_definition")
        )
        try:
            await dif_handler.verify_received_pres(pd=pres_definition, pres=dif_proof)
            return True
        except DIFPresExchError as err:
            LOGGER.error(str(err))
            responder = self._profile.inject_or(BaseResponder)
            if responder:
                report = ProblemReport(
                    description={
                        "en": str(err),
                        "code": ProblemReportReason.ABANDONED.value,
                    }
                )
                if pres_ex_record.thread_id:
                    report.assign_thread_id(pres_ex_record.thread_id)
                await responder.send_reply(
                    report, connection_id=pres_ex_record.connection_id
                )
                return False

    async def verify_pres(self, pres_ex_record: V30PresExRecord) -> V30PresExRecord:
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

            # TODO: check check if dif_proof contains vals afterwards
            dif_proof_atch = pres_ex_record.pres.attachments
            dif_proof = None
            for att in dif_proof_atch:
                if (
                    V30PresFormat.Format.get(att.format.format).api
                    == V30PresFormat.Format.DIF.api
                ):
                    dif_proof = att.content
            proof_request_atch = pres_ex_record.pres_request.attachments
            for att in proof_request_atch:
                if (
                    V30PresFormat.Format.get(att.format.format).api
                    == V30PresFormat.Format.DIF.api
                ):
                    pres_request = att.content
            challenge = None
            if "options" in pres_request:
                challenge = pres_request["options"].get("challenge", str(uuid4()))
            if not challenge:
                challenge = str(uuid4())
            pres_ver_result = await verify_presentation(
                presentation=dif_proof,
                suites=await self._get_all_suites(wallet=wallet),
                document_loader=self._profile.inject(DocumentLoader),
                challenge=challenge,
            )
            pres_ex_record.verified = json.dumps(pres_ver_result.verified)
            return pres_ex_record
