"""V2.0 issue-credential protocol manager."""

import asyncio
import json
import logging

from typing import Mapping, Tuple, Union

from ....cache.base import BaseCache
from ....core.error import BaseError
from ....core.profile import Profile
from ....indy.holder import IndyHolder, IndyHolderError
from ....indy.issuer import IndyIssuer, IndyIssuerRevocationRegistryFullError
from ....ledger.base import BaseLedger
from ....messaging.credential_definitions.util import CRED_DEF_SENT_RECORD_TYPE
from ....messaging.decorators.attach_decorator import AttachDecorator
from ....revocation.indy import IndyRevocation
from ....revocation.models.revocation_registry import RevocationRegistry
from ....revocation.models.issuer_rev_reg_record import IssuerRevRegRecord
from ....storage.base import BaseStorage
from ....storage.error import StorageNotFoundError

from .messages.cred_ack import V20CredAck
from .messages.cred_format import V20CredFormat
from .messages.cred_issue import V20CredIssue
from .messages.cred_offer import V20CredOffer
from .messages.cred_proposal import V20CredProposal
from .messages.cred_request import V20CredRequest
from .messages.inner.cred_preview import V20CredPreview
from .models.cred_ex_record import V20CredExRecord
from .models.detail.dif import V20CredExRecordDIF
from .models.detail.indy import V20CredExRecordIndy

LOGGER = logging.getLogger(__name__)


class V20CredManagerError(BaseError):
    """Credential manager error under issue-credential protocol v2.0."""


class V20CredManager:
    """Class for managing credentials."""

    def __init__(self, profile: Profile):
        """
        Initialize a V20CredManager.

        Args:
            profile: The profile instance for this credential manager
        """
        self._profile = profile

    @property
    def profile(self) -> Profile:
        """
        Accessor for the current profile instance.

        Returns:
            The profile instance for this credential manager

        """
        return self._profile

    async def _match_sent_cred_def_id(self, tag_query: Mapping[str, str]) -> str:
        """Return most recent matching id of cred def that agent sent to ledger."""

        async with self._profile.session() as session:
            storage = session.inject(BaseStorage)
            found = await storage.find_all_records(
                type_filter=CRED_DEF_SENT_RECORD_TYPE, tag_query=tag_query
            )
        if not found:
            raise V20CredManagerError(
                f"Issuer has no operable cred def for proposal spec {tag_query}"
            )
        return max(found, key=lambda r: int(r.tags["epoch"])).tags["cred_def_id"]

    async def get_detail_record(
        self,
        cred_ex_id: str,
        fmt: V20CredFormat.Format,
    ) -> Union[V20CredExRecordIndy, V20CredExRecordDIF]:
        """Retrieve credential exchange detail record by format."""

        async with self._profile.session() as session:
            detail_cls = fmt.detail
            try:
                return await detail_cls.retrieve_by_cred_ex_id(session, cred_ex_id)
            except StorageNotFoundError:
                return None

    async def prepare_send(
        self,
        conn_id: str,
        cred_proposal: V20CredProposal,
        auto_remove: bool = None,
    ) -> Tuple[V20CredExRecord, V20CredOffer]:
        """
        Set up a new credential exchange record for an automated send.

        Args:
            conn_id: connection for which to create offer
            cred_proposal: credential proposal with preview
            auto_remove: flag to remove the record automatically on completion

        Returns:
            A tuple of the new credential exchange record and credential offer message

        """
        if auto_remove is None:
            auto_remove = not self._profile.settings.get("preserve_exchange_records")
        cred_ex_record = V20CredExRecord(
            conn_id=conn_id,
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_ISSUER,
            cred_proposal=cred_proposal.serialize(),
            auto_issue=True,
            auto_remove=auto_remove,
            trace=(cred_proposal._trace is not None),
        )
        (cred_ex_record, cred_offer) = await self.create_offer(
            cred_ex_record=cred_ex_record,
            comment="create automated v2.0 credential exchange record",
        )
        return (cred_ex_record, cred_offer)

    async def create_proposal(
        self,
        conn_id: str,
        *,
        auto_remove: bool = None,
        comment: str = None,
        cred_preview: V20CredPreview,
        fmt2filter: Mapping[V20CredFormat.Format, Mapping[str, str]],
        trace: bool = False,
    ) -> V20CredExRecord:
        """
        Create a credential proposal.

        Args:
            conn_id: connection for which to create proposal
            auto_remove: whether to remove record automatically on completion
            comment: optional human-readable comment to include in proposal
            cred_preview: credential preview to use to create credential proposal
            fmt2filter: mapping between format and filter
            trace: whether to trace the operation

        Returns:
            Resulting credential exchange record including credential proposal

        """

        cred_proposal_message = V20CredProposal(
            comment=comment,
            credential_preview=cred_preview,
            formats=[
                V20CredFormat(attach_id=str(ident), format_=V20CredFormat.Format.get(f))
                for ident, f in enumerate(fmt2filter.keys())
            ],
            filters_attach=[
                AttachDecorator.data_base64(f or {}, ident=str(ident))
                for ident, f in enumerate(fmt2filter.values())
            ],
        )
        cred_proposal_message.assign_trace_decorator(self._profile.settings, trace)

        if auto_remove is None:
            auto_remove = not self._profile.settings.get("preserve_exchange_records")
        cred_ex_record = V20CredExRecord(
            conn_id=conn_id,
            thread_id=cred_proposal_message._thread_id,
            initiator=V20CredExRecord.INITIATOR_SELF,
            role=V20CredExRecord.ROLE_HOLDER,
            state=V20CredExRecord.STATE_PROPOSAL_SENT,
            cred_proposal=cred_proposal_message.serialize(),
            auto_remove=auto_remove,
            trace=trace,
        )
        async with self._profile.session() as session:
            await cred_ex_record.save(
                session,
                reason="create v2.0 credential proposal",
            )
        return cred_ex_record

    async def receive_proposal(
        self,
        cred_proposal_message: V20CredProposal,
        conn_id: str,
    ) -> V20CredExRecord:
        """
        Receive a credential proposal.

        Returns:
            The resulting credential exchange record, created

        """
        # at this point, cred def and schema still open to potential negotiation
        cred_ex_record = V20CredExRecord(
            conn_id=conn_id,
            thread_id=cred_proposal_message._thread_id,
            initiator=V20CredExRecord.INITIATOR_EXTERNAL,
            role=V20CredExRecord.ROLE_ISSUER,
            state=V20CredExRecord.STATE_PROPOSAL_RECEIVED,
            cred_proposal=cred_proposal_message.serialize(),
            auto_offer=self._profile.settings.get(
                "debug.auto_respond_credential_proposal"
            ),
            auto_issue=self._profile.settings.get(
                "debug.auto_respond_credential_request"
            ),
            auto_remove=not self._profile.settings.get("preserve_exchange_records"),
            trace=(cred_proposal_message._trace is not None),
        )
        async with self._profile.session() as session:
            await cred_ex_record.save(
                session,
                reason="receive v2.0 credential proposal",
            )

        return cred_ex_record

    async def create_offer(
        self,
        cred_ex_record: V20CredExRecord,
        replacement_id: str = None,
        comment: str = None,
    ) -> Tuple[V20CredExRecord, V20CredOffer]:
        """
        Create credential offer, update credential exchange record.

        Args:
            cred_ex_record: credential exchange record for which to create offer
            replacement_id: identifier to help coordinate credential replacement
            comment: optional human-readable comment to set in offer message

        Returns:
            A tuple (credential exchange record, credential offer message)

        """

        async def _create(cred_def_id):  # may change for DIF
            issuer = self._profile.inject(IndyIssuer)
            offer_json = await issuer.create_credential_offer(cred_def_id)
            return json.loads(offer_json)

        cred_proposal_message = V20CredProposal.deserialize(
            cred_ex_record.cred_proposal
        )
        cred_proposal_message.assign_trace_decorator(
            self._profile.settings, cred_ex_record.trace
        )

        assert V20CredFormat.Format.INDY in [
            V20CredFormat.Format.get(p.format) for p in cred_proposal_message.formats
        ]  # until DIF support

        cred_def_id = await self._match_sent_cred_def_id(
            V20CredFormat.Format.INDY.get_attachment_data(
                cred_proposal_message.formats,
                cred_proposal_message.filters_attach,
            )
        )
        cred_preview = cred_proposal_message.credential_preview

        # vet attributes
        ledger = self._profile.inject(BaseLedger)  # may change for DIF
        async with ledger:
            schema_id = await ledger.credential_definition_id2schema_id(cred_def_id)
            schema = await ledger.get_schema(schema_id)
        schema_attrs = {attr for attr in schema["attrNames"]}
        preview_attrs = {attr for attr in cred_preview.attr_dict()}
        if preview_attrs != schema_attrs:
            raise V20CredManagerError(
                f"Preview attributes {preview_attrs} "
                f"mismatch corresponding schema attributes {schema_attrs}"
            )

        cred_offer = None
        cache_key = f"credential_offer::{cred_def_id}"  # may change for DIF
        cache = self._profile.inject(BaseCache, required=False)
        if cache:
            async with cache.acquire(cache_key) as entry:
                if entry.result:
                    cred_offer = entry.result
                else:
                    cred_offer = await _create(cred_def_id)
                    await entry.set_result(cred_offer, 3600)
        if not cred_offer:
            cred_offer = await _create(cred_def_id)

        cred_offer_message = V20CredOffer(
            replacement_id=replacement_id,
            comment=comment,
            credential_preview=cred_preview,
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            offers_attach=[AttachDecorator.data_base64(cred_offer, ident="0")],
        )

        cred_offer_message._thread = {"thid": cred_ex_record.thread_id}
        cred_offer_message.assign_trace_decorator(
            self._profile.settings, cred_ex_record.trace
        )

        cred_ex_record.thread_id = cred_offer_message._thread_id
        cred_ex_record.state = V20CredExRecord.STATE_OFFER_SENT
        cred_ex_record.cred_offer = cred_offer_message.serialize()

        async with self._profile.session() as session:
            await cred_ex_record.save(session, reason="create v2.0 credential offer")

        return (cred_ex_record, cred_offer_message)

    async def receive_offer(
        self,
        cred_offer_message: V20CredOffer,
        conn_id: str,
    ) -> V20CredExRecord:
        """
        Receive a credential offer.

        Args:
            cred_offer_message: credential offer message
            conn_id: connection identifier

        Returns:
            The credential exchange record, updated

        """
        assert V20CredFormat.Format.INDY in [
            V20CredFormat.Format.get(p.format) for p in cred_offer_message.formats
        ]  # until DIF support

        offer = cred_offer_message.offer(
            V20CredFormat.Format.INDY
        )  # may change for DIF
        schema_id = offer["schema_id"]
        cred_def_id = offer["cred_def_id"]

        cred_proposal_ser = V20CredProposal(
            comment=cred_offer_message.comment,
            credential_preview=cred_offer_message.credential_preview,
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            filters_attach=[
                AttachDecorator.data_base64(
                    {
                        "schema_id": schema_id,
                        "cred_def_id": cred_def_id,
                    },
                    ident="0",
                )
            ],
        ).serialize()  # proposal houses filters, preview (possibly with MIME types)

        async with self._profile.session() as session:
            # Get credential exchange record (holder sent proposal first)
            # or create it (issuer sent offer first)
            try:
                cred_ex_record = await (
                    V20CredExRecord.retrieve_by_conn_and_thread(
                        session, conn_id, cred_offer_message._thread_id
                    )
                )
                cred_ex_record.cred_proposal = cred_proposal_ser
            except StorageNotFoundError:  # issuer sent this offer free of any proposal
                cred_ex_record = V20CredExRecord(
                    conn_id=conn_id,
                    thread_id=cred_offer_message._thread_id,
                    initiator=V20CredExRecord.INITIATOR_EXTERNAL,
                    role=V20CredExRecord.ROLE_HOLDER,
                    cred_proposal=cred_proposal_ser,
                    auto_remove=not self._profile.settings.get(
                        "preserve_exchange_records"
                    ),
                    trace=(cred_offer_message._trace is not None),
                )

            cred_ex_record.cred_offer = cred_offer_message.serialize()
            cred_ex_record.state = V20CredExRecord.STATE_OFFER_RECEIVED

            await cred_ex_record.save(session, reason="receive v2.0 credential offer")

        return cred_ex_record

    async def create_request(
        self, cred_ex_record: V20CredExRecord, holder_did: str, comment: str = None
    ) -> Tuple[V20CredExRecord, V20CredRequest]:
        """
        Create a credential request.

        Args:
            cred_ex_record: credential exchange record for which to create request
            holder_did: holder DID
            comment: optional human-readable comment to set in request message

        Returns:
            A tuple (credential exchange record, credential request message)

        """
        if cred_ex_record.state != V20CredExRecord.STATE_OFFER_RECEIVED:
            raise V20CredManagerError(  # indy-ism: must change for DIF
                f"Credential exchange {cred_ex_record.cred_ex_id} "
                f"in {cred_ex_record.state} state "
                f"(must be {V20CredExRecord.STATE_OFFER_RECEIVED})"
            )

        cred_offer_message = V20CredOffer.deserialize(cred_ex_record.cred_offer)
        cred_offer = cred_offer_message.offer(
            V20CredFormat.Format.INDY
        )  # will change for DIF
        cred_def_id = cred_offer["cred_def_id"]

        async def _create_indy():
            ledger = self._profile.inject(BaseLedger)
            async with ledger:
                cred_def = await ledger.get_credential_definition(cred_def_id)

            holder = self._profile.inject(IndyHolder)
            request_json, metadata_json = await holder.create_credential_request(
                cred_offer, cred_def, holder_did
            )
            return {
                "request": json.loads(request_json),
                "metadata": json.loads(metadata_json),
            }

        if cred_ex_record.cred_request:
            raise V20CredManagerError(
                "create_request() called multiple times for "
                f"v2.0 credential exchange {cred_ex_record.cred_ex_id}"
            )

        if "nonce" not in cred_offer:
            raise V20CredManagerError("Missing nonce in credential offer")
        nonce = cred_offer["nonce"]
        cache_key = f"credential_request::{cred_def_id}::{holder_did}::{nonce}"
        cred_req_result = None
        cache = self._profile.inject(BaseCache, required=False)
        if cache:
            async with cache.acquire(cache_key) as entry:
                if entry.result:
                    cred_req_result = entry.result
                else:
                    cred_req_result = await _create_indy()
                    await entry.set_result(cred_req_result, 3600)
        if not cred_req_result:
            cred_req_result = await _create_indy()

        detail_record = V20CredExRecordIndy(
            cred_ex_id=cred_ex_record.cred_ex_id,
            cred_request_metadata=cred_req_result["metadata"],
        )

        cred_request_message = V20CredRequest(
            comment=comment,
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            requests_attach=[
                AttachDecorator.data_base64(cred_req_result["request"], ident="0")
            ],
        )

        cred_request_message._thread = {"thid": cred_ex_record.thread_id}
        cred_request_message.assign_trace_decorator(
            self._profile.settings, cred_ex_record.trace
        )

        cred_ex_record.state = V20CredExRecord.STATE_REQUEST_SENT
        async with self._profile.session() as session:
            await cred_ex_record.save(session, reason="create v2.0 credential request")
            await detail_record.save(session, reason="create v2.0 credential request")

        return (cred_ex_record, cred_request_message)

    async def receive_request(
        self, cred_request_message: V20CredRequest, conn_id: str
    ) -> V20CredExRecord:
        """
        Receive a credential request.

        Args:
            cred_request_message: credential request to receive
            conn_id: connection identifier

        Returns:
            credential exchange record, retrieved and updated

        """
        assert len(cred_request_message.requests_attach or []) == 1

        async with self._profile.session() as session:
            cred_ex_record = await (
                V20CredExRecord.retrieve_by_conn_and_thread(
                    session, conn_id, cred_request_message._thread_id
                )
            )
            cred_ex_record.cred_request = cred_request_message.serialize()
            cred_ex_record.state = V20CredExRecord.STATE_REQUEST_RECEIVED
            await cred_ex_record.save(session, reason="receive v2.0 credential request")

        return cred_ex_record

    async def issue_credential(
        self,
        cred_ex_record: V20CredExRecord,
        *,
        comment: str = None,
        retries: int = 5,
    ) -> Tuple[V20CredExRecord, V20CredIssue]:
        """
        Issue a credential.

        Args:
            cred_ex_record: credential exchange record for which to issue credential
            comment: optional human-readable comment pertaining to credential issue
            retries: maximum number of retries on failure

        Returns:
            Tuple: (Updated credential exchange record, credential issue message)

        """

        if cred_ex_record.state != V20CredExRecord.STATE_REQUEST_RECEIVED:
            raise V20CredManagerError(
                f"Credential exchange {cred_ex_record.cred_ex_id} "
                f"in {cred_ex_record.state} state "
                f"(must be {V20CredExRecord.STATE_REQUEST_RECEIVED})"
            )

        cred_offer_message = V20CredOffer.deserialize(cred_ex_record.cred_offer)
        replacement_id = cred_offer_message.replacement_id
        cred_offer = cred_offer_message.offer(V20CredFormat.Format.INDY)
        schema_id = cred_offer["schema_id"]
        cred_def_id = cred_offer["cred_def_id"]

        cred_request = V20CredRequest.deserialize(
            cred_ex_record.cred_request
        ).cred_request(
            V20CredFormat.Format.INDY
        )  # will change for DIF

        rev_reg_id = None
        rev_reg = None

        if cred_ex_record.cred_issue:
            raise V20CredManagerError(
                "issue_credential() called multiple times for "
                f"cred ex record {cred_ex_record.cred_ex_id}"
            )

        ledger = self._profile.inject(BaseLedger)
        async with ledger:
            schema = await ledger.get_schema(schema_id)
            cred_def = await ledger.get_credential_definition(cred_def_id)

        tails_path = None
        if cred_def["value"].get("revocation"):
            revoc = IndyRevocation(self._profile)
            try:
                active_rev_reg_rec = await revoc.get_active_issuer_rev_reg_record(
                    cred_def_id
                )
                rev_reg = await active_rev_reg_rec.get_registry()
                rev_reg_id = active_rev_reg_rec.revoc_reg_id

                tails_path = rev_reg.tails_local_path
                await rev_reg.get_or_fetch_local_tails_path()

            except StorageNotFoundError:
                async with self._profile.session() as session:
                    posted_rev_reg_recs = await IssuerRevRegRecord.query_by_cred_def_id(
                        session,
                        cred_def_id,
                        state=IssuerRevRegRecord.STATE_POSTED,
                    )
                if not posted_rev_reg_recs:
                    # Send next 2 rev regs, publish tails files in background
                    async with self._profile.session() as session:
                        old_rev_reg_recs = sorted(
                            await IssuerRevRegRecord.query_by_cred_def_id(
                                session,
                                cred_def_id,
                            )
                        )  # prefer to reuse prior rev reg size
                    for _ in range(2):
                        pending_rev_reg_rec = await revoc.init_issuer_registry(
                            cred_def_id,
                            max_cred_num=(
                                old_rev_reg_recs[0].max_cred_num
                                if old_rev_reg_recs
                                else None
                            ),
                        )
                        asyncio.ensure_future(
                            pending_rev_reg_rec.stage_pending_registry(
                                self._profile,
                                max_attempts=3,  # fail both in < 2s at worst
                            )
                        )
                if retries > 0:
                    LOGGER.info(
                        ("Waiting 2s on posted rev reg " "for cred def %s, retrying"),
                        cred_def_id,
                    )
                    await asyncio.sleep(2)
                    return await self.issue_credential(
                        cred_ex_record=cred_ex_record,
                        comment=comment,
                        retries=retries - 1,
                    )

                raise V20CredManagerError(
                    f"Cred def id {cred_def_id} " "has no active revocation registry"
                )
            del revoc

        cred_values = V20CredProposal.deserialize(
            cred_ex_record.cred_proposal
        ).credential_preview.attr_dict(decode=False)
        issuer = self._profile.inject(IndyIssuer)
        try:
            (cred_json, cred_rev_id,) = await issuer.create_credential(
                schema,
                cred_offer,
                cred_request,
                cred_values,
                cred_ex_record.cred_ex_id,
                rev_reg_id,
                tails_path,
            )

            detail_record = V20CredExRecordIndy(
                cred_ex_id=cred_ex_record.cred_ex_id,
                rev_reg_id=rev_reg_id,
                cred_rev_id=cred_rev_id,
            )

            # If the rev reg is now full
            if rev_reg and rev_reg.max_creds == int(cred_rev_id):
                async with self._profile.session() as session:
                    await active_rev_reg_rec.set_state(
                        session,
                        IssuerRevRegRecord.STATE_FULL,
                    )

                # Send next 1 rev reg, publish tails file in background
                revoc = IndyRevocation(self._profile)
                pending_rev_reg_rec = await revoc.init_issuer_registry(
                    active_rev_reg_rec.cred_def_id,
                    max_cred_num=active_rev_reg_rec.max_cred_num,
                )
                asyncio.ensure_future(
                    pending_rev_reg_rec.stage_pending_registry(
                        self._profile,
                        max_attempts=16,
                    )
                )

        except IndyIssuerRevocationRegistryFullError:
            # unlucky: duelling instance issued last cred near same time as us
            async with self._profile.session() as session:
                await active_rev_reg_rec.set_state(
                    session,
                    IssuerRevRegRecord.STATE_FULL,
                )

            if retries > 0:
                # use next rev reg; at worst, lucky instance is putting one up
                LOGGER.info(
                    "Waiting 1s and retrying: revocation registry %s is full",
                    active_rev_reg_rec.revoc_reg_id,
                )
                await asyncio.sleep(1)
                return await self.issue_credential(
                    cred_ex_record=cred_ex_record,
                    comment=comment,
                    retries=retries - 1,
                )

            raise

        cred_issue_message = V20CredIssue(
            replacement_id=replacement_id,
            comment=comment,
            formats=[V20CredFormat(attach_id="0", format_=V20CredFormat.Format.INDY)],
            credentials_attach=[
                AttachDecorator.data_base64(json.loads(cred_json), ident="0")
            ],
        )

        cred_ex_record.state = V20CredExRecord.STATE_ISSUED
        cred_ex_record.cred_issue = cred_issue_message.serialize()
        async with self._profile.session() as session:
            # FIXME - re-fetch record to check state, apply transactional update
            await cred_ex_record.save(session, reason="v2.0 issue credential")
            await detail_record.save(session, reason="v2.0 issue credential")

        cred_issue_message._thread = {"thid": cred_ex_record.thread_id}
        cred_issue_message.assign_trace_decorator(
            self._profile.settings, cred_ex_record.trace
        )

        return (cred_ex_record, cred_issue_message)

    async def receive_credential(
        self, cred_issue_message: V20CredIssue, conn_id: str
    ) -> V20CredExRecord:
        """
        Receive a credential issue message from an issuer.

        Hold cred in storage potentially to be processed by controller before storing.

        Returns:
            Credential exchange record, retrieved and updated

        """
        assert cred_issue_message.credentials_attach

        # FIXME use transaction, fetch for_update
        async with self._profile.session() as session:
            cred_ex_record = await (
                V20CredExRecord.retrieve_by_conn_and_thread(
                    session,
                    conn_id,
                    cred_issue_message._thread_id,
                )
            )

            cred_ex_record.cred_issue = cred_issue_message.serialize()
            cred_ex_record.state = V20CredExRecord.STATE_CREDENTIAL_RECEIVED

            await cred_ex_record.save(session, reason="receive v2.0 credential issue")
        return cred_ex_record

    async def store_credential(
        self, cred_ex_record: V20CredExRecord, cred_id: str = None
    ) -> Tuple[V20CredExRecord, V20CredAck]:
        """
        Store a credential in holder wallet; send ack to issuer.

        Args:
            cred_ex_record: credential exchange record with credential to store and ack
            cred_id: optional credential identifier to override default on storage

        Returns:
            Tuple: (Updated credential exchange record, credential ack message)

        """
        if cred_ex_record.state != (V20CredExRecord.STATE_CREDENTIAL_RECEIVED):
            raise V20CredManagerError(
                f"Credential exchange {cred_ex_record.cred_ex_id} "
                f"in {cred_ex_record.state} state "
                f"(must be {V20CredExRecord.STATE_CREDENTIAL_RECEIVED})"
            )

        cred = V20CredIssue.deserialize(cred_ex_record.cred_issue).cred(
            V20CredFormat.Format.INDY
        )

        rev_reg_def = None
        ledger = self._profile.inject(BaseLedger)
        async with ledger:
            cred_def = await ledger.get_credential_definition(cred["cred_def_id"])
            if cred.get("rev_reg_id"):
                rev_reg_def = await ledger.get_revoc_reg_def(cred["rev_reg_id"])

        holder = self._profile.inject(IndyHolder)
        cred_proposal_message = V20CredProposal.deserialize(
            cred_ex_record.cred_proposal
        )
        mime_types = None
        if cred_proposal_message and cred_proposal_message.credential_preview:
            mime_types = cred_proposal_message.credential_preview.mime_types() or None

        if rev_reg_def:
            rev_reg = RevocationRegistry.from_definition(rev_reg_def, True)
            await rev_reg.get_or_fetch_local_tails_path()
        try:
            detail_record = await self.get_detail_record(
                cred_ex_record.cred_ex_id,
                V20CredFormat.Format.INDY,
            )
            if detail_record is None:
                raise V20CredManagerError(
                    f"No credential exchange {V20CredFormat.Format.INDY.aries} "
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
        except IndyHolderError as e:
            LOGGER.error(f"Error storing credential: {e.error_code} - {e.message}")
            raise e

        cred_ex_record.state = V20CredExRecord.STATE_DONE
        cred_ex_record.cred_id_stored = cred_id_stored
        detail_record.rev_reg_id = cred.get("rev_reg_id", None)
        detail_record.cred_rev_id = cred.get("cred_rev_id", None)

        async with self._profile.session() as session:
            # FIXME - re-fetch record to check state, apply transactional update
            await cred_ex_record.save(session, reason="store credential v2.0")
            await detail_record.save(session, reason="store credential v2.0")

        cred_ack_message = V20CredAck()
        cred_ack_message.assign_thread_id(
            cred_ex_record.thread_id, cred_ex_record.parent_thread_id
        )
        cred_ack_message.assign_trace_decorator(
            self._profile.settings, cred_ex_record.trace
        )

        if cred_ex_record.auto_remove:
            await self.delete_cred_ex_record(cred_ex_record.cred_ex_id)

        return (cred_ex_record, cred_ack_message)

    async def receive_credential_ack(
        self, cred_ack_message: V20CredAck, conn_id: str
    ) -> V20CredExRecord:
        """
        Receive credential ack from holder.

        Args:
            cred_ack_message: credential ack message to receive
            conn_id: connection identifier

        Returns:
            credential exchange record, retrieved and updated

        """
        # FIXME use transaction, fetch for_update
        async with self._profile.session() as session:
            cred_ex_record = await (
                V20CredExRecord.retrieve_by_conn_and_thread(
                    session,
                    conn_id,
                    cred_ack_message._thread_id,
                )
            )

            cred_ex_record.state = V20CredExRecord.STATE_DONE
            await cred_ex_record.save(session, reason="receive credential ack v2.0")

        if cred_ex_record.auto_remove:
            await self.delete_cred_ex_record(cred_ex_record.cred_ex_id)

        return cred_ex_record

    async def delete_cred_ex_record(self, cred_ex_id: str) -> None:
        """Delete credential exchange record and associated detail records."""

        async with self._profile.session() as session:
            for fmt in V20CredFormat.Format:  # details first: do not strand any orphans
                try:
                    detail_record = await fmt.detail.retrieve_by_cred_ex_id(
                        session,
                        cred_ex_id,
                    )
                    await detail_record.delete_record(session)
                except StorageNotFoundError:
                    pass

            cred_ex_record = await V20CredExRecord.retrieve_by_id(session, cred_ex_id)
            await cred_ex_record.delete_record(session)
