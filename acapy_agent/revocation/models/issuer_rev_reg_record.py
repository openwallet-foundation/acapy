"""Issuer revocation registry storage handling."""

import importlib
import json
import logging
from functools import total_ordering
from os.path import join
from pathlib import Path
from shutil import move
from typing import Any, Mapping, Optional, Sequence, Tuple, Union
from urllib.parse import urlparse

from marshmallow import fields, validate
from uuid_utils import uuid4

from ...core.profile import Profile, ProfileSession
from ...indy.credx.issuer import (
    CATEGORY_CRED_DEF,
    CATEGORY_REV_REG,
    CATEGORY_REV_REG_DEF_PRIVATE,
)
from ...indy.issuer import IndyIssuer, IndyIssuerError
from ...indy.models.revocation import (
    IndyRevRegDef,
    IndyRevRegDefSchema,
    IndyRevRegEntry,
    IndyRevRegEntrySchema,
)
from ...indy.util import indy_client_dir
from ...ledger.base import BaseLedger
from ...ledger.error import LedgerError, LedgerTransactionError
from ...messaging.models.base_record import BaseRecord, BaseRecordSchema
from ...messaging.valid import (
    BASE58_SHA256_HASH_EXAMPLE,
    BASE58_SHA256_HASH_VALIDATE,
    INDY_CRED_DEF_ID_EXAMPLE,
    INDY_CRED_DEF_ID_VALIDATE,
    INDY_DID_EXAMPLE,
    INDY_DID_VALIDATE,
    INDY_REV_REG_ID_EXAMPLE,
    INDY_REV_REG_ID_VALIDATE,
    UUID4_EXAMPLE,
)
from ...tails.indy_tails_server import IndyTailsServer
from ..error import RevocationError
from ..recover import generate_ledger_rrrecovery_txn
from .issuer_cred_rev_record import IssuerCredRevRecord
from .revocation_registry import RevocationRegistry

DEFAULT_REGISTRY_SIZE = 1000

LOGGER = logging.getLogger(__name__)


@total_ordering
class IssuerRevRegRecord(BaseRecord):
    """Class for managing local issuing revocation registries."""

    class Meta:
        """IssuerRevRegRecord metadata."""

        schema_class = "IssuerRevRegRecordSchema"

    RECORD_ID_NAME = "record_id"
    RECORD_TYPE = "issuer_rev_reg"
    RECORD_TOPIC = "revocation_registry"
    LOG_STATE_FLAG = "debug.revocation"
    TAG_NAMES = {
        "cred_def_id",
        "issuer_did",
        "revoc_def_type",
        "revoc_reg_id",
        "state",
    }

    REVOC_DEF_TYPE_CL = "CL_ACCUM"

    STATE_INIT = "init"
    STATE_GENERATED = "generated"
    STATE_POSTED = "posted"  # definition published
    STATE_ACTIVE = "active"  # initial entry published, possibly subsequent entries
    STATE_FULL = "full"  # includes corrupt
    STATE_DECOMMISSIONED = "decommissioned"

    STATES = [
        STATE_INIT,
        STATE_GENERATED,
        STATE_POSTED,
        STATE_ACTIVE,
        STATE_FULL,
        STATE_DECOMMISSIONED,
    ]
    TERMINAL_STATES = [STATE_FULL, STATE_DECOMMISSIONED]

    def __init__(
        self,
        *,
        record_id: Optional[str] = None,
        state: Optional[str] = None,
        cred_def_id: Optional[str] = None,
        error_msg: Optional[str] = None,
        issuer_did: Optional[str] = None,
        max_cred_num: Optional[int] = None,
        revoc_def_type: Optional[str] = None,
        revoc_reg_id: Optional[str] = None,
        revoc_reg_def: Union[IndyRevRegDef, Mapping] = None,
        revoc_reg_entry: Union[IndyRevRegEntry, Mapping] = None,
        tag: Optional[str] = None,
        tails_hash: Optional[str] = None,
        tails_local_path: Optional[str] = None,
        tails_public_uri: Optional[str] = None,
        pending_pub: Sequence[str] = None,
        **kwargs,
    ):
        """Initialize the issuer revocation registry record."""
        super().__init__(
            record_id, state=state or IssuerRevRegRecord.STATE_INIT, **kwargs
        )
        self.cred_def_id = cred_def_id
        self.error_msg = error_msg
        self.issuer_did = issuer_did
        self.max_cred_num = max_cred_num or DEFAULT_REGISTRY_SIZE
        self.revoc_def_type = revoc_def_type or self.REVOC_DEF_TYPE_CL
        self.revoc_reg_id = revoc_reg_id
        self._revoc_reg_def = IndyRevRegDef.serde(revoc_reg_def)
        self._revoc_reg_entry = IndyRevRegEntry.serde(revoc_reg_entry)
        self.tag = tag
        self.tails_hash = tails_hash
        self.tails_local_path = tails_local_path
        self.tails_public_uri = tails_public_uri
        self.pending_pub = (
            sorted(set(pending_pub)) if pending_pub else []
        )  # order for eq comparison between instances

    @property
    def record_id(self) -> str:
        """Accessor for the record ID."""
        return self._id

    @property
    def revoc_reg_def(self) -> IndyRevRegDef:
        """Accessor; get deserialized."""
        return None if self._revoc_reg_def is None else self._revoc_reg_def.de

    @revoc_reg_def.setter
    def revoc_reg_def(self, value):
        """Setter; store de/serialized views."""
        self._revoc_reg_def = IndyRevRegDef.serde(value)

    @property
    def revoc_reg_entry(self) -> IndyRevRegEntry:
        """Accessor; get deserialized."""
        return None if self._revoc_reg_entry is None else self._revoc_reg_entry.de

    @revoc_reg_entry.setter
    def revoc_reg_entry(self, value):
        """Setter; store de/serialized views."""
        self._revoc_reg_entry = IndyRevRegEntry.serde(value)

    @property
    def record_value(self) -> Mapping:
        """Accessor for JSON value properties of this revocation registry record."""
        return {
            **{
                prop: getattr(self, prop)
                for prop in (
                    "error_msg",
                    "max_cred_num",
                    "tag",
                    "tails_hash",
                    "tails_public_uri",
                    "tails_local_path",
                    "pending_pub",
                )
            },
            **{
                prop: getattr(self, f"_{prop}").ser
                for prop in (
                    "revoc_reg_def",
                    "revoc_reg_entry",
                )
                if getattr(self, prop) is not None
            },
        }

    def _check_url(self, url) -> None:
        parsed = urlparse(url)
        if not (parsed.scheme and parsed.netloc and parsed.path):
            raise RevocationError("URI {} is not a valid URL".format(url))

    async def generate_registry(self, profile: Profile):
        """Create the revocation registry definition and tails file."""
        if not self.tag:
            self.tag = self._id or str(uuid4())

        if self.state != IssuerRevRegRecord.STATE_INIT:
            raise RevocationError(
                "Revocation registry {} in state {}: cannot generate".format(
                    self.revoc_reg_id, self.state
                )
            )

        issuer = profile.inject(IndyIssuer)
        tails_hopper_dir = indy_client_dir(join("tails", ".hopper"), create=True)

        LOGGER.debug("Creating revocation registry with size: %d", self.max_cred_num)

        try:
            (
                revoc_reg_id,
                revoc_reg_def_json,
                revoc_reg_entry_json,
            ) = await issuer.create_and_store_revocation_registry(
                self.issuer_did,
                self.cred_def_id,
                self.revoc_def_type,
                self.tag,
                self.max_cred_num,
                tails_hopper_dir,
            )
        except IndyIssuerError as err:
            raise RevocationError() from err

        if self.revoc_reg_id and revoc_reg_id != self.revoc_reg_id:
            raise RevocationError("Generated registry ID does not match assigned value")
        self.revoc_reg_id = revoc_reg_id
        self.revoc_reg_def = json.loads(revoc_reg_def_json)
        self.revoc_reg_entry = json.loads(revoc_reg_entry_json)
        self.state = IssuerRevRegRecord.STATE_GENERATED
        self.tails_hash = self.revoc_reg_def.value.tails_hash

        tails_dir = indy_client_dir(join("tails", self.revoc_reg_id), create=True)
        tails_path = join(tails_dir, self.tails_hash)
        move(join(tails_hopper_dir, self.tails_hash), tails_path)
        self.tails_local_path = tails_path

        async with profile.session() as session:
            await self.save(session, reason="Generated registry")

    async def set_tails_file_public_uri(self, profile: Profile, tails_file_uri: str):
        """Update tails file's publicly accessible URI."""
        if not (self.revoc_reg_def and self.revoc_reg_def.value.tails_location):
            raise RevocationError("Revocation registry undefined")

        self._check_url(tails_file_uri)

        self.tails_public_uri = tails_file_uri
        self._revoc_reg_def.de.value.tails_location = tails_file_uri  # update ...
        self.revoc_reg_def = self._revoc_reg_def.de  # ... and pick up change via setter
        async with profile.session() as session:
            await self.save(session, reason="Set tails file public URI")

    async def send_def(
        self,
        profile: Profile,
        write_ledger: bool = True,
        endorser_did: Optional[str] = None,
    ) -> dict:
        """Send the revocation registry definition to the ledger."""
        if not (self.revoc_reg_def and self.issuer_did):
            raise RevocationError(f"Revocation registry {self.revoc_reg_id} undefined")

        self._check_url(self.tails_public_uri)

        if self.state != IssuerRevRegRecord.STATE_GENERATED:
            raise RevocationError(
                "Revocation registry {} in state {}: cannot publish definition".format(
                    self.revoc_reg_id, self.state
                )
            )

        ledger = profile.inject(BaseLedger)
        async with ledger:
            rev_reg_res = await ledger.send_revoc_reg_def(
                self._revoc_reg_def.ser,
                self.issuer_did,
                write_ledger=write_ledger,
                endorser_did=endorser_did,
            )

        self.state = IssuerRevRegRecord.STATE_POSTED
        async with profile.session() as session:
            await self.save(session, reason="Published revocation registry definition")

        return rev_reg_res

    async def send_entry(
        self,
        profile: Profile,
        write_ledger: bool = True,
        endorser_did: Optional[str] = None,
    ) -> dict:
        """Send a registry entry to the ledger."""
        if not (
            self.revoc_reg_id
            and self.revoc_def_type
            and self.revoc_reg_entry
            and self.issuer_did
        ):
            raise RevocationError("Revocation registry undefined")

        self._check_url(self.tails_public_uri)

        if self.state not in (
            IssuerRevRegRecord.STATE_POSTED,
            IssuerRevRegRecord.STATE_ACTIVE,
            IssuerRevRegRecord.STATE_DECOMMISSIONED,
            IssuerRevRegRecord.STATE_FULL,  # can still publish revocation deltas
        ):
            raise RevocationError(
                "Revocation registry {} in state {}: cannot publish entry".format(
                    self.revoc_reg_id, self.state
                )
            )

        ledger = profile.inject(BaseLedger)
        async with ledger:
            try:
                rev_entry_res = await ledger.send_revoc_reg_entry(
                    self.revoc_reg_id,
                    self.revoc_def_type,
                    self._revoc_reg_entry.ser,
                    self.issuer_did,
                    write_ledger=write_ledger,
                    endorser_did=endorser_did,
                )
            except LedgerTransactionError as err:
                if "InvalidClientRequest" in err.roll_up:
                    # ... if the ledger write fails (with "InvalidClientRequest")
                    # e.g. acapy_agent.ledger.error.LedgerTransactionError:
                    #   Ledger rejected transaction request: client request invalid:
                    #   InvalidClientRequest(...)
                    # In this scenario we try to post a correction
                    LOGGER.warning("Retry ledger update/fix due to error")
                    LOGGER.warning(err)
                    (_, _, res) = await self.fix_ledger_entry(
                        profile,
                        True,
                        ledger.pool.genesis_txns,
                    )
                    rev_entry_res = {"result": res}
                    LOGGER.warning("Ledger update/fix applied")
                elif "InvalidClientTaaAcceptanceError" in err.roll_up:
                    # if no write access (with "InvalidClientTaaAcceptanceError")
                    # e.g. acapy_agent.ledger.error.LedgerTransactionError:
                    #   Ledger rejected transaction request: client request invalid:
                    #   InvalidClientTaaAcceptanceError(...)
                    LOGGER.error("Ledger update failed due to TAA issue")
                    LOGGER.error(err)
                    raise err
                else:
                    # not sure what happened, raise an error
                    LOGGER.error("Ledger update failed due to unknown issue")
                    LOGGER.error(err)
                    raise err
        if self.state == IssuerRevRegRecord.STATE_POSTED:
            self.state = IssuerRevRegRecord.STATE_ACTIVE  # initial entry activates
            async with profile.session() as session:
                await self.save(
                    session, reason="Published initial revocation registry entry"
                )

        return rev_entry_res

    def _get_revoked_discrepancies(
        self, recs: Sequence[IssuerCredRevRecord], rev_reg_delta: dict
    ) -> Tuple[list, int]:
        revoked_ids = []
        rec_count = 0
        for rec in recs:
            if rec.state == IssuerCredRevRecord.STATE_REVOKED:
                revoked_ids.append(int(rec.cred_rev_id))
                if int(rec.cred_rev_id) not in rev_reg_delta["value"]["revoked"]:
                    rec_count += 1

        return revoked_ids, rec_count

    async def fix_ledger_entry(
        self,
        profile: Profile,
        apply_ledger_update: bool,
        genesis_transactions: str,
    ) -> Tuple[dict, dict, dict]:
        """Fix the ledger entry to match wallet-recorded credentials."""
        recovery_txn = {}
        applied_txn = {}

        # get rev reg delta (revocations published to ledger)
        ledger = profile.inject(BaseLedger)
        async with ledger:
            (rev_reg_delta, _) = await ledger.get_revoc_reg_delta(self.revoc_reg_id)

        # get rev reg records from wallet (revocations and status)
        async with profile.session() as session:
            recs = await IssuerCredRevRecord.query_by_ids(
                session, rev_reg_id=self.revoc_reg_id
            )

        revoked_ids, rec_count = self._get_revoked_discrepancies(recs, rev_reg_delta)

        LOGGER.debug(f"Fixed entry recs count = {rec_count}")
        LOGGER.debug(f"Rev reg entry value: {self.revoc_reg_entry.value}")
        LOGGER.debug(f"Rev reg delta: {rev_reg_delta.get('value')}")

        # No update required if no discrepancies
        if rec_count == 0:
            return (rev_reg_delta, {}, {})

        # We have revocation discrepancies, generate the recovery txn
        async with profile.session() as session:
            # We need the cred_def and rev_reg_def_private to generate the recovery txn
            issuer_rev_reg_record = await IssuerRevRegRecord.retrieve_by_revoc_reg_id(
                session, self.revoc_reg_id
            )
            cred_def_id = issuer_rev_reg_record.cred_def_id
            cred_def = await session.handle.fetch(CATEGORY_CRED_DEF, cred_def_id)
            rev_reg_def_private = await session.handle.fetch(
                CATEGORY_REV_REG_DEF_PRIVATE, self.revoc_reg_id
            )

        credx_module = importlib.import_module("indy_credx")
        cred_defn = credx_module.CredentialDefinition.load(cred_def.value_json)
        rev_reg_defn_private = credx_module.RevocationRegistryDefinitionPrivate.load(
            rev_reg_def_private.value_json
        )
        calculated_txn = await generate_ledger_rrrecovery_txn(
            genesis_transactions,
            self.revoc_reg_id,
            revoked_ids,
            cred_defn,
            rev_reg_defn_private,
        )
        recovery_txn = json.loads(calculated_txn.to_json())

        LOGGER.debug(f"Applying ledger update: {apply_ledger_update}")
        if apply_ledger_update:
            async with profile.session() as session:
                ledger = session.inject_or(BaseLedger)
                if not ledger:
                    reason = "No ledger available"
                    if not session.context.settings.get_value("wallet.type"):
                        reason += ": missing wallet-type?"
                    raise LedgerError(reason=reason)

                async with ledger:
                    ledger_response = await ledger.send_revoc_reg_entry(
                        self.revoc_reg_id, "CL_ACCUM", recovery_txn
                    )

            applied_txn = ledger_response["result"]

            # Update the local wallets rev reg entry with the new accumulator value
            async with profile.session() as session:
                rev_reg = await session.handle.fetch(
                    CATEGORY_REV_REG, self.revoc_reg_id, for_update=True
                )
                new_value_json = rev_reg.value_json
                new_value_json["value"]["accum"] = applied_txn["txn"]["data"]["value"][
                    "accum"
                ]
                await session.handle.replace(
                    CATEGORY_REV_REG,
                    rev_reg.name,
                    json.dumps(new_value_json),
                    rev_reg.tags,
                )

        return (rev_reg_delta, recovery_txn, applied_txn)

    @property
    def has_local_tails_file(self) -> bool:
        """Check if a local copy of the tails file is available."""
        return bool(self.tails_local_path) and Path(self.tails_local_path).is_file()

    async def upload_tails_file(self, profile: Profile):
        """Upload the local tails file to the tails server."""
        tails_server = IndyTailsServer()
        if not self.has_local_tails_file:
            raise RevocationError("Local tails file not found")

        (upload_success, result) = await tails_server.upload_tails_file(
            profile.context,
            self.revoc_reg_id,
            self.tails_local_path,
            interval=0.8,
            backoff=-0.5,
            max_attempts=5,  # heuristic: respect HTTP timeout
        )
        if not upload_success:
            raise RevocationError(
                f"Tails file for rev reg {self.revoc_reg_id} failed to upload: {result}"
            )
        await self.set_tails_file_public_uri(profile, result)

    async def mark_pending(self, session: ProfileSession, cred_rev_id: str) -> None:
        """Mark a credential revocation id as revoked pending publication to ledger.

        Args:
            session: The profile session to use
            cred_rev_id: The credential revocation identifier for credential to revoke
        """
        if cred_rev_id not in self.pending_pub:
            self.pending_pub.append(cred_rev_id)
            self.pending_pub.sort()

        await self.save(session, reason="Marked pending revocation")

    async def clear_pending(
        self, session: ProfileSession, cred_rev_ids: Sequence[str] = None
    ) -> None:
        """Clear pending revocations and save any resulting record change.

        Args:
            session: The profile session to use
            cred_rev_ids: Credential revocation identifiers to clear; default all
        """
        if self.pending_pub:
            if cred_rev_ids:
                self.pending_pub = [r for r in self.pending_pub if r not in cred_rev_ids]
            else:
                self.pending_pub.clear()
            await self.save(session, reason="Cleared pending revocations")

    def get_registry(self) -> RevocationRegistry:
        """Create a `RevocationRegistry` instance from this record."""
        return RevocationRegistry(
            self.revoc_reg_id,
            cred_def_id=self.cred_def_id,
            issuer_did=self.issuer_did,
            max_creds=self.max_cred_num,
            reg_def_type=self.revoc_def_type,
            tag=self.tag,
            tails_local_path=self.tails_local_path,
            tails_public_uri=self.tails_public_uri,
            tails_hash=self.tails_hash,
        )

    @classmethod
    async def query_by_cred_def_id(
        cls,
        session: ProfileSession,
        cred_def_id: str,
        state: Optional[str] = None,
        negative_state: Optional[str] = None,
        limit=None,
    ) -> Sequence["IssuerRevRegRecord"]:
        """Retrieve issuer revocation registry records by credential definition ID.

        Args:
            session: The profile session to use
            cred_def_id: The credential definition ID to filter by
            state: A state value to filter by
            negative_state: A state value to exclude
            limit: The maximum number of records to return
        """
        tag_filter = dict(
            filter(
                lambda f: f[1] is not None,
                (("cred_def_id", cred_def_id), ("state", state)),
            )
        )
        return await cls.query(
            session,
            tag_filter,
            post_filter_positive={"state": state} if state else None,
            post_filter_negative={"state": negative_state} if negative_state else None,
            limit=limit,
        )

    @classmethod
    async def query_by_pending(
        cls, session: ProfileSession
    ) -> Sequence["IssuerRevRegRecord"]:
        """Retrieve issuer revocation records with revocations pending.

        Args:
            session: The profile session to use
        """
        return await cls.query(
            session=session,
            tag_filter=None,
            post_filter_positive=None,
            post_filter_negative={"pending_pub": []},
        )

    @classmethod
    async def retrieve_by_revoc_reg_id(
        cls, session: ProfileSession, revoc_reg_id: str, for_update: bool = False
    ) -> "IssuerRevRegRecord":
        """Retrieve a revocation registry record by revocation registry ID.

        Args:
            session: The profile session to use
            revoc_reg_id: The revocation registry ID
            for_update: Retrieve for update
        """
        tag_filter = {"revoc_reg_id": revoc_reg_id}
        return await cls.retrieve_by_tag_filter(
            session, tag_filter, for_update=for_update
        )

    async def set_state(self, session: ProfileSession, state: Optional[str] = None):
        """Change the registry state (default full)."""
        self.state = state or IssuerRevRegRecord.STATE_FULL
        await self.save(
            session, reason=f"Marked rev reg {self.revoc_reg_id} as {self.state}"
        )

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)

    def __lt__(self, other):
        """Order by creation time."""
        return (self.created_at or 0) < (other.created_at or 0)


class IssuerRevRegRecordSchema(BaseRecordSchema):
    """Schema to allow serialization/deserialization of issuer rev reg records."""

    class Meta:
        """IssuerRevRegRecordSchema metadata."""

        model_class = IssuerRevRegRecord

    record_id = fields.Str(
        required=False,
        metadata={
            "description": "Issuer revocation registry record identifier",
            "example": UUID4_EXAMPLE,
        },
    )
    state = fields.Str(
        required=False,
        metadata={
            "description": "Issue revocation registry record state",
            "example": IssuerRevRegRecord.STATE_ACTIVE,
        },
    )
    cred_def_id = fields.Str(
        required=False,
        validate=INDY_CRED_DEF_ID_VALIDATE,
        metadata={
            "description": "Credential definition identifier",
            "example": INDY_CRED_DEF_ID_EXAMPLE,
        },
    )
    error_msg = fields.Str(
        required=False,
        metadata={
            "description": "Error message",
            "example": "Revocation registry undefined",
        },
    )
    issuer_did = fields.Str(
        required=False,
        validate=INDY_DID_VALIDATE,
        metadata={"description": "Issuer DID", "example": INDY_DID_EXAMPLE},
    )
    max_cred_num = fields.Int(
        required=False,
        metadata={
            "description": "Maximum number of credentials for revocation registry",
            "strict": True,
            "example": 1000,
        },
    )
    revoc_def_type = fields.Str(
        required=False,
        validate=validate.Equal("CL_ACCUM"),
        metadata={
            "description": "Revocation registry type (specify CL_ACCUM)",
            "example": "CL_ACCUM",
        },
    )
    revoc_reg_id = fields.Str(
        required=False,
        validate=INDY_REV_REG_ID_VALIDATE,
        metadata={
            "description": "Revocation registry identifier",
            "example": INDY_REV_REG_ID_EXAMPLE,
        },
    )
    revoc_reg_def = fields.Nested(
        IndyRevRegDefSchema(),
        required=False,
        metadata={"description": "Revocation registry definition"},
    )
    revoc_reg_entry = fields.Nested(
        IndyRevRegEntrySchema(),
        required=False,
        metadata={"description": "Revocation registry entry"},
    )
    tag = fields.Str(
        required=False,
        metadata={"description": "Tag within issuer revocation registry identifier"},
    )
    tails_hash = fields.Str(
        required=False,
        validate=BASE58_SHA256_HASH_VALIDATE,
        metadata={"description": "Tails hash", "example": BASE58_SHA256_HASH_EXAMPLE},
    )
    tails_public_uri = fields.Str(
        required=False, metadata={"description": "Public URI for tails file"}
    )
    tails_local_path = fields.Str(
        required=False, metadata={"description": "Local path to tails file"}
    )
    pending_pub = fields.List(
        fields.Str(metadata={"example": "23"}),
        required=False,
        metadata={
            "description": (
                "Credential revocation identifier for credential revoked and pending"
                " publication to ledger"
            )
        },
    )
