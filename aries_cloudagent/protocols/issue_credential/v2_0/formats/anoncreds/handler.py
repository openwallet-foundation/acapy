"""V2.0 issue-credential indy credential format handler."""

import json
import logging
from typing import Mapping, Tuple

from marshmallow import RAISE

from ......anoncreds.revocation import AnonCredsRevocation

from ......anoncreds.registry import AnonCredsRegistry
from ......anoncreds.holder import AnonCredsHolder, AnonCredsHolderError
from ......anoncreds.issuer import (
    AnonCredsIssuer,
)
from ......indy.models.cred import IndyCredentialSchema
from ......indy.models.cred_abstract import IndyCredAbstractSchema
from ......indy.models.cred_request import IndyCredRequestSchema
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

LOGGER = logging.getLogger(__name__)


class AnonCredsCredFormatHandler(V20CredFormatHandler):
    """Indy credential format handler."""

    format = V20CredFormat.Format.INDY

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
                The attachment data to validate

        Raises:
            Exception: When the data is not valid.

        """
        mapping = {
            CRED_20_PROPOSAL: CredDefQueryStringSchema,
            CRED_20_OFFER: IndyCredAbstractSchema,
            CRED_20_REQUEST: IndyCredRequestSchema,
            CRED_20_ISSUE: IndyCredentialSchema,
        }

        # Get schema class
        Schema = mapping[message_type]

        # Validate, throw if not valid
        Schema(unknown=RAISE).load(attachment_data)

    async def get_detail_record(self, cred_ex_id: str) -> V20CredExRecordIndy:
        """Retrieve credential exchange detail record by cred_ex_id."""

        async with self.profile.session() as session:
            records = (
                await AnonCredsCredFormatHandler.format.detail.query_by_cred_ex_id(
                    session, cred_ex_id
                )
            )

        if len(records) > 1:
            LOGGER.warning(
                "Cred ex id %s has %d %s detail records: should be 1",
                cred_ex_id,
                len(records),
                AnonCredsCredFormatHandler.format.api,
            )
        return records[0] if records else None

    async def _check_uniqueness(self, cred_ex_id: str):
        """Raise exception on evidence that cred ex already has cred issued to it."""
        async with self.profile.session() as session:
            exist = await AnonCredsCredFormatHandler.format.detail.query_by_cred_ex_id(
                session, cred_ex_id
            )
        if exist:
            raise V20CredFormatError(
                f"{AnonCredsCredFormatHandler.format.api} detail record already "
                f"exists for cred ex id {cred_ex_id}"
            )

    def get_format_identifier(self, message_type: str) -> str:
        """Get attachment format identifier for format and message combination.

        Args:
            message_type (str): Message type for which to return the format identifier

        Returns:
            str: Issue credential attachment format identifier

        """
        return ATTACHMENT_FORMAT[message_type][AnonCredsCredFormatHandler.format.api]

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
                attach_id=AnonCredsCredFormatHandler.format.api,
                format_=self.get_format_identifier(message_type),
            ),
            AttachDecorator.data_base64(
                data, ident=AnonCredsCredFormatHandler.format.api
            ),
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
        """Create indy credential proposal."""
        if proposal_data is None:
            proposal_data = {}

        return self.get_format_data(CRED_20_PROPOSAL, proposal_data)

    async def receive_proposal(
        self, cred_ex_record: V20CredExRecord, cred_proposal_message: V20CredProposal
    ) -> None:
        """Receive indy credential proposal.

        No custom handling is required for this step.
        """

    async def create_offer(
        self, cred_proposal_message: V20CredProposal
    ) -> CredFormatAttachment:
        """Create indy credential offer."""

        issuer = AnonCredsIssuer(self.profile)
        ledger = self.profile.inject(BaseLedger)
        cache = self.profile.inject_or(BaseCache)

        cred_def_id = await issuer.match_created_credential_definitions(
            **cred_proposal_message.attachment(AnonCredsCredFormatHandler.format)
        )

        async def _create():
            offer_json = await issuer.create_credential_offer(cred_def_id)
            return json.loads(offer_json)

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

        return self.get_format_data(CRED_20_OFFER, cred_offer)

    async def receive_offer(
        self, cred_ex_record: V20CredExRecord, cred_offer_message: V20CredOffer
    ) -> None:
        """Receive indy credential offer."""

    async def create_request(
        self, cred_ex_record: V20CredExRecord, request_data: Mapping = None
    ) -> CredFormatAttachment:
        """Create indy credential request."""
        if cred_ex_record.state != V20CredExRecord.STATE_OFFER_RECEIVED:
            raise V20CredFormatError(
                "Indy issue credential format cannot start from credential request"
            )

        await self._check_uniqueness(cred_ex_record.cred_ex_id)

        holder_did = request_data.get("holder_did") if request_data else None
        cred_offer = cred_ex_record.cred_offer.attachment(
            AnonCredsCredFormatHandler.format
        )

        if "nonce" not in cred_offer:
            raise V20CredFormatError("Missing nonce in credential offer")

        nonce = cred_offer["nonce"]
        cred_def_id = cred_offer["cred_def_id"]

        async def _create():
            anoncreds_registry = self.profile.inject(AnonCredsRegistry)

            cred_def_result = await anoncreds_registry.get_credential_definition(
                self.profile, cred_def_id
            )

            holder = AnonCredsHolder(self.profile)
            request_json, metadata_json = await holder.create_credential_request(
                cred_offer, cred_def_result.credential_definition, holder_did
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

        async with self.profile.session() as session:
            await detail_record.save(session, reason="create v2.0 credential request")

        return self.get_format_data(CRED_20_REQUEST, cred_req_result["request"])

    async def receive_request(
        self, cred_ex_record: V20CredExRecord, cred_request_message: V20CredRequest
    ) -> None:
        """Receive indy credential request."""
        if not cred_ex_record.cred_offer:
            raise V20CredFormatError(
                "Indy issue credential format cannot start from credential request"
            )

    async def issue_credential(
        self, cred_ex_record: V20CredExRecord, retries: int = 5
    ) -> CredFormatAttachment:
        """Issue indy credential."""
        await self._check_uniqueness(cred_ex_record.cred_ex_id)

        cred_offer = cred_ex_record.cred_offer.attachment(
            AnonCredsCredFormatHandler.format
        )
        cred_request = cred_ex_record.cred_request.attachment(
            AnonCredsCredFormatHandler.format
        )
        cred_values = cred_ex_record.cred_offer.credential_preview.attr_dict(
            decode=False
        )

        issuer = AnonCredsIssuer(self.profile)
        cred_def_id = cred_offer["cred_def_id"]
        if await issuer.cred_def_supports_revocation(cred_def_id):
            revocation = AnonCredsRevocation(self.profile)
            cred_json, cred_rev_id, rev_reg_def_id = await revocation.create_credential(
                cred_offer, cred_request, cred_values
            )
        else:
            cred_json = await issuer.create_credential(
                cred_offer, cred_request, cred_values
            )
            cred_rev_id = None
            rev_reg_def_id = None

        result = self.get_format_data(CRED_20_ISSUE, json.loads(cred_json))

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

    async def receive_credential(
        self, cred_ex_record: V20CredExRecord, cred_issue_message: V20CredIssue
    ) -> None:
        """Receive indy credential.

        Validation is done in the store credential step.
        """

    async def store_credential(
        self, cred_ex_record: V20CredExRecord, cred_id: str = None
    ) -> None:
        """Store indy credential."""
        cred = cred_ex_record.cred_issue.attachment(AnonCredsCredFormatHandler.format)

        rev_reg_def = None
        anoncreds_registry = self.profile.inject(AnonCredsRegistry)
        cred_def_result = await anoncreds_registry.get_credential_definition(
            self.profile, cred["cred_def_id"]
        )
        if cred.get("rev_reg_id"):
            rev_reg_def_result = (
                await anoncreds_registry.get_revocation_registry_definition(
                    self.profile, cred["rev_reg_id"]
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
                    f"No credential exchange {AnonCredsCredFormatHandler.format.aries} "
                    f"detail record found for cred ex id {cred_ex_record.cred_ex_id}"
                )
            cred_id_stored = await holder.store_credential(
                cred_def_result.credential_definition.serialize(),
                cred,
                detail_record.cred_request_metadata,
                mime_types,
                credential_id=cred_id,
                rev_reg_def=rev_reg_def.serialize() if rev_reg_def else None,
            )

            detail_record.cred_id_stored = cred_id_stored
            detail_record.rev_reg_id = cred.get("rev_reg_id", None)
            detail_record.cred_rev_id = cred.get("cred_rev_id", None)

            async with self.profile.session() as session:
                # Store detail record, emit event
                await detail_record.save(
                    session, reason="store credential v2.0", event=True
                )
        except AnonCredsHolderError as e:
            LOGGER.error(f"Error storing credential: {e.error_code} - {e.message}")
            raise e
