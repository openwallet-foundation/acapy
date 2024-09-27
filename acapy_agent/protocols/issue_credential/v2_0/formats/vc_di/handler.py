"""V2.0 issue-credential vc_di credential format handler.

indy compatible, attachment is a valid verifiable credential
"""

import datetime
import json
import logging
from typing import Mapping, Optional, Tuple

from anoncreds import W3cCredential
from marshmallow import RAISE

from ......anoncreds.holder import AnonCredsHolder, AnonCredsHolderError
from ......anoncreds.issuer import AnonCredsIssuer
from ......anoncreds.registry import AnonCredsRegistry
from ......anoncreds.revocation import AnonCredsRevocation
from ......cache.base import BaseCache
from ......ledger.base import BaseLedger
from ......ledger.multiple_ledger.ledger_requests_executor import (
    GET_CRED_DEF,
    IndyLedgerRequestsExecutor,
)
from ......messaging.credential_definitions.util import (
    CRED_DEF_SENT_RECORD_TYPE,
    CredDefQueryStringSchema,
)
from ......messaging.decorators.attach_decorator import AttachDecorator
from ......multitenant.base import BaseMultitenantManager
from ......revocation_anoncreds.models.issuer_cred_rev_record import IssuerCredRevRecord
from ......storage.base import BaseStorage
from ......vc.vc_ld import VerifiableCredential
from ......wallet.base import BaseWallet
from ...message_types import (
    ATTACHMENT_FORMAT,
    CRED_20_ISSUE,
    CRED_20_OFFER,
    CRED_20_PROPOSAL,
    CRED_20_REQUEST,
)
from ...messages.cred_format import V20CredFormat
from ...messages.cred_issue import V20CredIssue
from ...messages.cred_offer import V20CredOffer
from ...messages.cred_proposal import V20CredProposal
from ...messages.cred_request import V20CredRequest
from ...models.cred_ex_record import V20CredExRecord
from ...models.detail.indy import V20CredExRecordIndy
from ..handler import CredFormatAttachment, V20CredFormatError, V20CredFormatHandler
from .models.cred import VCDIIndyCredentialSchema
from .models.cred_offer import (
    AnoncredsLinkSecret,
    BindingMethod,
    DidcommSignedAttachment,
    VCDICredAbstract,
    VCDICredAbstractSchema,
)
from .models.cred_request import (
    AnoncredsLinkSecretRequest,
    BindingProof,
    DidcommSignedAttachmentRequest,
    VCDICredRequest,
    VCDICredRequestSchema,
)

LOGGER = logging.getLogger(__name__)


class VCDICredFormatHandler(V20CredFormatHandler):
    """VCDI credential format handler."""

    format = V20CredFormat.Format.VC_DI

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
            CRED_20_PROPOSAL: CredDefQueryStringSchema,
            CRED_20_OFFER: VCDICredAbstractSchema,
            CRED_20_REQUEST: VCDICredRequestSchema,
            CRED_20_ISSUE: VCDIIndyCredentialSchema,
        }

        # Get schema class
        Schema = mapping[message_type]

        # Validate, throw if not valid
        Schema(unknown=RAISE).load(attachment_data)

    async def get_detail_record(self, cred_ex_id: str) -> V20CredExRecordIndy:
        """Retrieve credential exchange detail record by cred_ex_id."""

        async with self.profile.session() as session:
            records = await VCDICredFormatHandler.format.detail.query_by_cred_ex_id(
                session, cred_ex_id
            )

        if len(records) > 1:
            LOGGER.warning(
                "Cred ex id %s has %d %s detail records: should be 1",
                cred_ex_id,
                len(records),
                VCDICredFormatHandler.format.api,
            )
        return records[0] if records else None

    async def _check_uniqueness(self, cred_ex_id: str):
        """Raise exception on evidence that cred ex already has cred issued to it."""
        async with self.profile.session() as session:
            exist = await VCDICredFormatHandler.format.detail.query_by_cred_ex_id(
                session, cred_ex_id
            )
        if exist:
            raise V20CredFormatError(
                f"{VCDICredFormatHandler.format.api} detail record already "
                f"exists for cred ex id {cred_ex_id}"
            )

    def get_format_identifier(self, message_type: str) -> str:
        """Get attachment format identifier for format and message combination.

        Args:
            message_type (str): Message type for which to return the format identifier
        Returns:
            str: Issue credential attachment format identifier
        """
        return ATTACHMENT_FORMAT[message_type][VCDICredFormatHandler.format.api]

    def get_format_data(self, message_type: str, data: dict) -> CredFormatAttachment:
        """Get credential format and attachment objects for use in cred ex messages.

        Returns a tuple of both credential format and attachment decorator for use
        in credential exchange messages. It looks up the correct format identifier and
        encodes the data as a base64 attachment.

        Args:
            message_type (str): The message type for which to return the cred format.
                Should be one of the message types defined in the message types file
            data (dict): The data to include in the attach decorator
        Returns:
            CredFormatAttachment: Credential format and attachment data objects
        """
        return (
            V20CredFormat(
                attach_id=VCDICredFormatHandler.format.api,
                format_=self.get_format_identifier(message_type),
            ),
            AttachDecorator.data_base64(data, ident=VCDICredFormatHandler.format.api),
        )

    async def _match_sent_cred_def_id(self, tag_query: Mapping[str, str]) -> str:
        """Return most recent matching id of cred def that agent sent to ledger."""

        async with self.profile.session() as session:
            storage = session.inject(BaseStorage)
            found = await storage.find_all_records(
                type_filter=CRED_DEF_SENT_RECORD_TYPE, tag_query=tag_query
            )
        if not found:
            raise V20CredFormatError(
                f"Issuer has no operable cred def for proposal spec {tag_query}"
            )
        return max(found, key=lambda r: int(r.tags["epoch"])).tags["cred_def_id"]

    async def create_proposal(
        self, cred_ex_record: V20CredExRecord, proposal_data: Mapping[str, str]
    ) -> Tuple[V20CredFormat, AttachDecorator]:
        """Create vc_di credential proposal."""
        if proposal_data is None:
            proposal_data = {}

        return self.get_format_data(CRED_20_PROPOSAL, proposal_data)

    async def receive_proposal(
        self,
        cred_ex_record: V20CredExRecord,
        cred_proposal_message: V20CredProposal,
    ) -> None:
        """Receive vcdi credential proposal.

        No custom handling is required for this step.
        """

    async def create_offer(
        self, cred_proposal_message: V20CredProposal
    ) -> CredFormatAttachment:
        """Create vcdi credential offer."""

        issuer = AnonCredsIssuer(self.profile)
        # TODO use the ledger registry in the anoncreds module,
        # or move the functionality into the ledger class.
        ledger = self.profile.inject(BaseLedger)
        cache = self.profile.inject_or(BaseCache)

        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            public_did_info = await wallet.get_public_did()
            public_did = public_did_info.did

        cred_def_id = await issuer.match_created_credential_definitions(
            **cred_proposal_message.attachment(VCDICredFormatHandler.format)
        )

        async def _create():
            offer_str = await issuer.create_credential_offer(cred_def_id)
            return json.loads(offer_str)

        # TODO use the ledger registry in the anoncreds module,
        # or move the functionality into the ledger class.
        multitenant_mgr = self.profile.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(self.profile)
        else:
            ledger_exec_inst = self.profile.inject(IndyLedgerRequestsExecutor)
        ledger = (
            await ledger_exec_inst.get_ledger_for_identifier(
                cred_def_id,
                txn_record_type=GET_CRED_DEF,
            )
        )[1]
        # TODO use the ledger registry in the anoncreds module,
        # or move the functionality into the ledger class.
        async with ledger:
            schema_id = await ledger.credential_definition_id2schema_id(cred_def_id)
            schema = await ledger.get_schema(schema_id)
        schema_attrs = set(schema["attrNames"])
        preview_attrs = set(cred_proposal_message.credential_preview.attr_dict())
        if preview_attrs != schema_attrs:
            raise V20CredFormatError(
                f"Preview attributes {preview_attrs} "
                f"mismatch corresponding schema attributes {schema_attrs}"
            )

        cred_offer = None
        cache_key = f"credential_offer::{cred_def_id}"

        if cache:
            async with cache.acquire(cache_key) as entry:
                if entry.result:
                    cred_offer = entry.result
                else:
                    cred_offer = await _create()
                    await entry.set_result(cred_offer, 3600)
        if not cred_offer:
            cred_offer = await _create()

        credential = VerifiableCredential(
            issuer=public_did,
            credential_subject=cred_proposal_message.credential_preview.attr_dict(),
            issuance_date=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

        anoncreds_link_secret_instance = AnoncredsLinkSecret(
            cred_def_id=cred_offer["cred_def_id"],
            key_correctness_proof=cred_offer["key_correctness_proof"],
            nonce=cred_offer["nonce"],
        )

        didcomm_signed_attachment_instance = DidcommSignedAttachment(
            algs_supported=["EdDSA"],
            did_methods_supported=["key"],
            nonce=cred_offer["nonce"],
        )

        binding_method_instance = BindingMethod(
            anoncreds_link_secret=anoncreds_link_secret_instance,
            didcomm_signed_attachment=didcomm_signed_attachment_instance,
        )

        vcdi_cred_abstract = VCDICredAbstract(
            data_model_versions_supported=["1.1"],
            binding_required=True,
            binding_method=binding_method_instance,
            credential=credential,
        )

        cred_offer = self.get_format_data(
            CRED_20_OFFER, json.loads(vcdi_cred_abstract.to_json())
        )
        return cred_offer

    async def receive_offer(
        self, cred_ex_record: V20CredExRecord, cred_offer_message: V20CredOffer
    ) -> None:
        """Receive vcdi credential offer."""

    async def create_request(
        self, cred_ex_record: V20CredExRecord, request_data: Optional[Mapping] = None
    ) -> CredFormatAttachment:
        """Create vcdi credential request."""
        if cred_ex_record.state != V20CredExRecord.STATE_OFFER_RECEIVED:
            raise V20CredFormatError(
                "vcdi issue credential format cannot start from credential request"
            )

        await self._check_uniqueness(cred_ex_record.cred_ex_id)

        holder_did = request_data.get("holder_did") if request_data else None
        cred_offer = cred_ex_record.cred_offer.attachment(VCDICredFormatHandler.format)

        if (
            "anoncreds_link_secret" in cred_offer["binding_method"]
            and "nonce" not in cred_offer["binding_method"]["anoncreds_link_secret"]
        ):
            raise V20CredFormatError(
                "Missing nonce in credential offer with anoncreds link secret "
                "binding method"
            )

        nonce = cred_offer["binding_method"]["anoncreds_link_secret"]["nonce"]
        cred_def_id = cred_offer["binding_method"]["anoncreds_link_secret"]["cred_def_id"]

        ledger = self.profile.inject(BaseLedger)
        # TODO use the ledger registry in the anoncreds module,
        # or move the functionality into the ledger class.
        multitenant_mgr = self.profile.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(self.profile)
        else:
            ledger_exec_inst = self.profile.inject(IndyLedgerRequestsExecutor)
        ledger = (
            await ledger_exec_inst.get_ledger_for_identifier(
                cred_def_id,
                txn_record_type=GET_CRED_DEF,
            )
        )[1]

        async with ledger:
            schema_id = await ledger.credential_definition_id2schema_id(cred_def_id)

        async def _create():
            anoncreds_registry = self.profile.inject(AnonCredsRegistry)

            cred_def_result = await anoncreds_registry.get_credential_definition(
                self.profile, cred_def_id
            )

            legacy_offer = await self._prepare_legacy_offer(cred_offer, schema_id)

            holder = AnonCredsHolder(self.profile)
            request_json, metadata_json = await holder.create_credential_request(
                legacy_offer, cred_def_result.credential_definition, holder_did
            )

            return {
                "request": json.loads(request_json),
                "metadata": json.loads(metadata_json),
            }

        cache_key = f"credential_request::{cred_def_id}::{holder_did}::{nonce}"
        cred_req_result = None
        cache = self.profile.inject_or(BaseCache)
        if cache:
            async with cache.acquire(cache_key) as entry:
                if entry.result:
                    cred_req_result = entry.result
                else:
                    cred_req_result = await _create()
                    await entry.set_result(cred_req_result, 3600)
        if not cred_req_result:
            cred_req_result = await _create()
        detail_record = V20CredExRecordIndy(
            cred_ex_id=cred_ex_record.cred_ex_id,
            cred_request_metadata=cred_req_result["metadata"],
        )

        anoncreds_link_secret_instance = AnoncredsLinkSecretRequest(
            entropy=cred_req_result["request"]["prover_did"],
            cred_def_id=cred_req_result["request"]["cred_def_id"],
            blinded_ms=cred_req_result["request"]["blinded_ms"],
            blinded_ms_correctness_proof=cred_req_result["request"][
                "blinded_ms_correctness_proof"
            ],
            nonce=cred_req_result["request"]["nonce"],
        )

        didcomm_signed_attachment_instance = DidcommSignedAttachmentRequest(
            attachment_id="test"
        )

        binding_proof_instance = BindingProof(
            anoncreds_link_secret=anoncreds_link_secret_instance,
            didcomm_signed_attachment=didcomm_signed_attachment_instance,
        )

        vcdi_cred_request = VCDICredRequest(
            data_model_version="2.0", binding_proof=binding_proof_instance
        )

        async with self.profile.session() as session:
            await detail_record.save(session, reason="create v2.0 credential request")

        return self.get_format_data(
            CRED_20_REQUEST, json.loads(vcdi_cred_request.to_json())
        )

    async def receive_request(
        self, cred_ex_record: V20CredExRecord, cred_request_message: V20CredRequest
    ) -> None:
        """Receive vcdi credential request."""
        if not cred_ex_record.cred_offer:
            raise V20CredFormatError(
                "vcdi issue credential format cannot start from credential request"
            )

    async def issue_credential(
        self, cred_ex_record: V20CredExRecord, retries: int = 5
    ) -> CredFormatAttachment:
        """Issue vcdi credential."""
        await self._check_uniqueness(cred_ex_record.cred_ex_id)

        cred_offer = cred_ex_record.cred_offer.attachment(VCDICredFormatHandler.format)
        cred_request = cred_ex_record.cred_request.attachment(
            VCDICredFormatHandler.format
        )
        cred_values = cred_ex_record.cred_offer.credential_preview.attr_dict(decode=False)

        cred_def_id = cred_offer["binding_method"]["anoncreds_link_secret"]["cred_def_id"]

        ledger = self.profile.inject(BaseLedger)
        # TODO use the ledger registry in the anoncreds module,
        # or move the functionality into the ledger class.
        multitenant_mgr = self.profile.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(self.profile)
        else:
            ledger_exec_inst = self.profile.inject(IndyLedgerRequestsExecutor)
        ledger = (
            await ledger_exec_inst.get_ledger_for_identifier(
                cred_def_id,
                txn_record_type=GET_CRED_DEF,
            )
        )[1]

        async with ledger:
            schema_id = await ledger.credential_definition_id2schema_id(cred_def_id)
            cred_def = await ledger.get_credential_definition(cred_def_id)
        revocable = True if cred_def["value"].get("revocation") else False

        legacy_offer = await self._prepare_legacy_offer(cred_offer, schema_id)
        legacy_request = await self._prepare_legacy_request(cred_request, cred_def_id)

        cred_rev_id = None
        rev_reg_def_id = None
        credential = None
        if revocable:
            issuer = AnonCredsRevocation(self.profile)
            (
                credential,
                cred_rev_id,
                rev_reg_def_id,
            ) = await issuer.create_credential_w3c(
                legacy_offer, legacy_request, cred_values
            )
        else:
            issuer = AnonCredsIssuer(self.profile)
            credential = await issuer.create_credential_w3c(
                legacy_offer, legacy_request, cred_values
            )

        vcdi_credential = {
            "credential": json.loads(credential),
        }

        result = self.get_format_data(CRED_20_ISSUE, vcdi_credential)

        async with self._profile.transaction() as txn:
            detail_record = V20CredExRecordIndy(
                cred_ex_id=cred_ex_record.cred_ex_id,
                rev_reg_id=rev_reg_def_id,
                cred_rev_id=cred_rev_id,
            )
            await detail_record.save(txn, reason="v2.0 issue credential")

            if cred_rev_id:
                issuer_cr_rec = IssuerCredRevRecord(
                    state=IssuerCredRevRecord.STATE_ISSUED,
                    cred_ex_id=cred_ex_record.cred_ex_id,
                    cred_ex_version=IssuerCredRevRecord.VERSION_2,
                    rev_reg_id=rev_reg_def_id,
                    cred_rev_id=cred_rev_id,
                )
                await issuer_cr_rec.save(
                    txn,
                    reason=(
                        "Created issuer cred rev record for "
                        f"rev reg id {rev_reg_def_id}, index {cred_rev_id}"
                    ),
                )
            await txn.commit()

        return result

    async def _prepare_legacy_offer(self, cred_offer: dict, schema_id: str) -> dict:
        """Convert current offer to legacy offer format."""
        return {
            "schema_id": schema_id,
            "cred_def_id": cred_offer["binding_method"]["anoncreds_link_secret"][
                "cred_def_id"
            ],
            "key_correctness_proof": cred_offer["binding_method"][
                "anoncreds_link_secret"
            ]["key_correctness_proof"],
            "nonce": cred_offer["binding_method"]["anoncreds_link_secret"]["nonce"],
        }

    async def _prepare_legacy_request(self, cred_request: dict, cred_def_id: str):
        return {
            "prover_did": cred_request["binding_proof"]["anoncreds_link_secret"][
                "entropy"
            ],
            "cred_def_id": cred_def_id,
            "blinded_ms": cred_request["binding_proof"]["anoncreds_link_secret"][
                "blinded_ms"
            ],
            "blinded_ms_correctness_proof": cred_request["binding_proof"][
                "anoncreds_link_secret"
            ]["blinded_ms_correctness_proof"],
            "nonce": cred_request["binding_proof"]["anoncreds_link_secret"]["nonce"],
        }

    async def receive_credential(
        self, cred_ex_record: V20CredExRecord, cred_issue_message: V20CredIssue
    ) -> None:
        """Receive vcdi credential.

        Validation is done in the store credential step.
        """

    async def store_credential(
        self, cred_ex_record: V20CredExRecord, cred_id: Optional[str] = None
    ) -> None:
        """Store vcdi credential."""
        cred = cred_ex_record.cred_issue.attachment(VCDICredFormatHandler.format)
        cred = cred["credential"]
        try:
            w3cred = W3cCredential.load(cred)
        except AnonCredsHolderError as e:
            LOGGER.error(f"Error receiving credential: {e.error_code} - {e.message}")
        rev_reg_def = None
        anoncreds_registry = self.profile.inject(AnonCredsRegistry)
        cred_def_result = await anoncreds_registry.get_credential_definition(
            self.profile, cred["proof"][0]["verificationMethod"]
        )
        rev_reg_id = None
        rev_reg_index = None
        if (
            w3cred.rev_reg_id != "None"
        ):  # String None because rev_reg_id property wrapped str()
            rev_reg_id = w3cred.rev_reg_id

            rev_reg_def_result = (
                await anoncreds_registry.get_revocation_registry_definition(
                    self.profile, rev_reg_id
                )
            )
            rev_reg_def = rev_reg_def_result.revocation_registry

        holder = AnonCredsHolder(self.profile)
        cred_offer_message = cred_ex_record.cred_offer
        mime_types = None
        if cred_offer_message and cred_offer_message.credential_preview:
            mime_types = cred_offer_message.credential_preview.mime_types() or None

        if rev_reg_def:
            revocation = AnonCredsRevocation(self.profile)
            await revocation.get_or_fetch_local_tails_path(rev_reg_def)
        try:
            detail_record = await self.get_detail_record(cred_ex_record.cred_ex_id)
            if detail_record is None:
                raise V20CredFormatError(
                    f"No credential exchange {VCDICredFormatHandler.format.aries} "
                    f"detail record found for cred ex id {cred_ex_record.cred_ex_id}"
                )
            cred_id_stored = await holder.store_credential_w3c(
                cred_def_result.credential_definition.serialize(),
                cred,
                detail_record.cred_request_metadata,
                mime_types,
                credential_id=cred_id,
                rev_reg_def=rev_reg_def.serialize() if rev_reg_def else None,
            )

            detail_record.cred_id_stored = cred_id_stored
            detail_record.rev_reg_id = rev_reg_id
            detail_record.cred_rev_id = rev_reg_index

            async with self.profile.session() as session:
                # Store detail record, emit event
                await detail_record.save(
                    session, reason="store credential v2.0", event=True
                )
        except AnonCredsHolderError as e:
            LOGGER.error(f"Error storing credential: {e.error_code} - {e.message}")
            raise e
