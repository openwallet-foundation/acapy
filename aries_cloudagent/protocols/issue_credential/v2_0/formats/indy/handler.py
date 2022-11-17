"""V2.0 issue-credential indy credential format handler."""

import logging

from marshmallow import RAISE
import json
from typing import Mapping, Tuple
import asyncio

from ......cache.base import BaseCache
from ......indy.issuer import IndyIssuer, IndyIssuerRevocationRegistryFullError
from ......indy.holder import IndyHolder, IndyHolderError
from ......indy.models.cred import IndyCredentialSchema
from ......indy.models.cred_request import IndyCredRequestSchema
from ......indy.models.cred_abstract import IndyCredAbstractSchema
from ......ledger.base import BaseLedger
from ......ledger.multiple_ledger.ledger_requests_executor import (
    GET_CRED_DEF,
    GET_SCHEMA,
    IndyLedgerRequestsExecutor,
)
from ......messaging.credential_definitions.util import (
    CRED_DEF_SENT_RECORD_TYPE,
    CredDefQueryStringSchema,
)
from ......messaging.decorators.attach_decorator import AttachDecorator
from ......multitenant.base import BaseMultitenantManager
from ......revocation.indy import IndyRevocation
from ......revocation.models.issuer_cred_rev_record import IssuerCredRevRecord
from ......revocation.models.revocation_registry import RevocationRegistry
from ......storage.base import BaseStorage

from ...message_types import (
    ATTACHMENT_FORMAT,
    CRED_20_ISSUE,
    CRED_20_OFFER,
    CRED_20_PROPOSAL,
    CRED_20_REQUEST,
)
from ...messages.cred_format import V20CredFormat
from ...messages.cred_proposal import V20CredProposal
from ...messages.cred_offer import V20CredOffer
from ...messages.cred_request import V20CredRequest
from ...messages.cred_issue import V20CredIssue
from ...models.cred_ex_record import V20CredExRecord
from ...models.detail.indy import V20CredExRecordIndy

from ..handler import CredFormatAttachment, V20CredFormatError, V20CredFormatHandler

LOGGER = logging.getLogger(__name__)


class IndyCredFormatHandler(V20CredFormatHandler):
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
                The attachment data to valide

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
            records = await IndyCredFormatHandler.format.detail.query_by_cred_ex_id(
                session, cred_ex_id
            )

        if len(records) > 1:
            LOGGER.warning(
                "Cred ex id %s has %d %s detail records: should be 1",
                cred_ex_id,
                len(records),
                IndyCredFormatHandler.format.api,
            )
        return records[0] if records else None

    async def _check_uniqueness(self, cred_ex_id: str):
        """Raise exception on evidence that cred ex already has cred issued to it."""
        async with self.profile.session() as session:
            exist = await IndyCredFormatHandler.format.detail.query_by_cred_ex_id(
                session, cred_ex_id
            )
        if exist:
            raise V20CredFormatError(
                f"{IndyCredFormatHandler.format.api} detail record already "
                f"exists for cred ex id {cred_ex_id}"
            )

    def get_format_identifier(self, message_type: str) -> str:
        """Get attachment format identifier for format and message combination.

        Args:
            message_type (str): Message type for which to return the format identifier

        Returns:
            str: Issue credential attachment format identifier

        """
        return ATTACHMENT_FORMAT[message_type][IndyCredFormatHandler.format.api]

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
                attach_id=IndyCredFormatHandler.format.api,
                format_=self.get_format_identifier(message_type),
            ),
            AttachDecorator.data_base64(data, ident=IndyCredFormatHandler.format.api),
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

        issuer = self.profile.inject(IndyIssuer)
        ledger = self.profile.inject(BaseLedger)
        cache = self.profile.inject_or(BaseCache)

        cred_def_id = await self._match_sent_cred_def_id(
            cred_proposal_message.attachment(IndyCredFormatHandler.format)
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
        schema_attrs = {attr for attr in schema["attrNames"]}
        preview_attrs = {
            attr for attr in cred_proposal_message.credential_preview.attr_dict()
        }
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
        cred_offer = cred_ex_record.cred_offer.attachment(IndyCredFormatHandler.format)

        if "nonce" not in cred_offer:
            raise V20CredFormatError("Missing nonce in credential offer")

        nonce = cred_offer["nonce"]
        cred_def_id = cred_offer["cred_def_id"]

        async def _create():
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
                cred_def = await ledger.get_credential_definition(cred_def_id)

            holder = self.profile.inject(IndyHolder)
            request_json, metadata_json = await holder.create_credential_request(
                cred_offer, cred_def, holder_did
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

        cred_offer = cred_ex_record.cred_offer.attachment(IndyCredFormatHandler.format)
        cred_request = cred_ex_record.cred_request.attachment(
            IndyCredFormatHandler.format
        )
        cred_values = cred_ex_record.cred_offer.credential_preview.attr_dict(
            decode=False
        )
        schema_id = cred_offer["schema_id"]
        cred_def_id = cred_offer["cred_def_id"]

        issuer = self.profile.inject(IndyIssuer)
        multitenant_mgr = self.profile.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(self.profile)
        else:
            ledger_exec_inst = self.profile.inject(IndyLedgerRequestsExecutor)
        ledger = (
            await ledger_exec_inst.get_ledger_for_identifier(
                schema_id,
                txn_record_type=GET_SCHEMA,
            )
        )[1]
        async with ledger:
            schema = await ledger.get_schema(schema_id)
            cred_def = await ledger.get_credential_definition(cred_def_id)
        revocable = cred_def["value"].get("revocation")
        result = None

        for attempt in range(max(retries, 1)):
            if attempt > 0:
                LOGGER.info(
                    "Waiting 2s before retrying credential issuance for cred def '%s'",
                    cred_def_id,
                )
                await asyncio.sleep(2)

            if revocable:
                revoc = IndyRevocation(self.profile)
                registry_info = await revoc.get_or_create_active_registry(cred_def_id)
                if not registry_info:
                    continue
                del revoc
                issuer_rev_reg, rev_reg = registry_info
                rev_reg_id = issuer_rev_reg.revoc_reg_id
                tails_path = rev_reg.tails_local_path
            else:
                rev_reg_id = None
                tails_path = None

            try:
                (cred_json, cred_rev_id) = await issuer.create_credential(
                    schema,
                    cred_offer,
                    cred_request,
                    cred_values,
                    rev_reg_id,
                    tails_path,
                )
            except IndyIssuerRevocationRegistryFullError:
                # unlucky, another instance filled the registry first
                continue

            if revocable and rev_reg.max_creds <= int(cred_rev_id):
                revoc = IndyRevocation(self.profile)
                await revoc.handle_full_registry(rev_reg_id)
                del revoc

            result = self.get_format_data(CRED_20_ISSUE, json.loads(cred_json))
            break

        if not result:
            raise V20CredFormatError(
                f"Cred def '{cred_def_id}' has no active revocation registry"
            )

        async with self._profile.transaction() as txn:
            detail_record = V20CredExRecordIndy(
                cred_ex_id=cred_ex_record.cred_ex_id,
                rev_reg_id=rev_reg_id,
                cred_rev_id=cred_rev_id,
            )
            await detail_record.save(txn, reason="v2.0 issue credential")

            if revocable and cred_rev_id:
                issuer_cr_rec = IssuerCredRevRecord(
                    state=IssuerCredRevRecord.STATE_ISSUED,
                    cred_ex_id=cred_ex_record.cred_ex_id,
                    cred_ex_version=IssuerCredRevRecord.VERSION_2,
                    rev_reg_id=rev_reg_id,
                    cred_rev_id=cred_rev_id,
                )
                await issuer_cr_rec.save(
                    txn,
                    reason=(
                        "Created issuer cred rev record for "
                        f"rev reg id {rev_reg_id}, index {cred_rev_id}"
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
        cred = cred_ex_record.cred_issue.attachment(IndyCredFormatHandler.format)

        rev_reg_def = None
        multitenant_mgr = self.profile.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(self.profile)
        else:
            ledger_exec_inst = self.profile.inject(IndyLedgerRequestsExecutor)
        ledger = (
            await ledger_exec_inst.get_ledger_for_identifier(
                cred["cred_def_id"],
                txn_record_type=GET_CRED_DEF,
            )
        )[1]
        async with ledger:
            cred_def = await ledger.get_credential_definition(cred["cred_def_id"])
            if cred.get("rev_reg_id"):
                rev_reg_def = await ledger.get_revoc_reg_def(cred["rev_reg_id"])

        holder = self.profile.inject(IndyHolder)
        cred_offer_message = cred_ex_record.cred_offer
        mime_types = None
        if cred_offer_message and cred_offer_message.credential_preview:
            mime_types = cred_offer_message.credential_preview.mime_types() or None

        if rev_reg_def:
            rev_reg = RevocationRegistry.from_definition(rev_reg_def, True)
            await rev_reg.get_or_fetch_local_tails_path()
        try:
            detail_record = await self.get_detail_record(cred_ex_record.cred_ex_id)
            if detail_record is None:
                raise V20CredFormatError(
                    f"No credential exchange {IndyCredFormatHandler.format.aries} "
                    f"detail record found for cred ex id {cred_ex_record.cred_ex_id}"
                )
            cred_id_stored = await holder.store_credential(
                cred_def,
                cred,
                detail_record.cred_request_metadata,
                mime_types,
                credential_id=cred_id,
                rev_reg_def=rev_reg_def,
            )

            detail_record.cred_id_stored = cred_id_stored
            detail_record.rev_reg_id = cred.get("rev_reg_id", None)
            detail_record.cred_rev_id = cred.get("cred_rev_id", None)

            async with self.profile.session() as session:
                # Store detail record, emit event
                await detail_record.save(
                    session, reason="store credential v2.0", event=True
                )
        except IndyHolderError as e:
            LOGGER.error(f"Error storing credential: {e.error_code} - {e.message}")
            raise e
