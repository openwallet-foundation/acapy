"""Issuer revocation registry storage handling."""

import json
import logging
import uuid

from asyncio import shield
from os.path import join
from shutil import move
from typing import Any, Sequence
from urllib.parse import urlparse

from marshmallow import fields, validate

from ...tails.base import BaseTailsServer
from ...config.injection_context import InjectionContext
from ...indy.util import indy_client_dir
from ...issuer.base import BaseIssuer, IssuerError
from ...messaging.models.base_record import BaseRecord, BaseRecordSchema
from ...messaging.valid import (
    BASE58_SHA256_HASH,
    INDY_CRED_DEF_ID,
    INDY_DID,
    INDY_REV_REG_ID,
    UUIDFour,
)
from ...ledger.base import BaseLedger

from ..error import RevocationError

from .revocation_registry import RevocationRegistry

DEFAULT_REGISTRY_SIZE = 100

LOGGER = logging.getLogger(__name__)


class IssuerRevRegRecord(BaseRecord):
    """Class for managing local issuing revocation registries."""

    class Meta:
        """IssuerRevRegRecord metadata."""

        schema_class = "IssuerRevRegRecordSchema"

    RECORD_ID_NAME = "record_id"
    RECORD_TYPE = "issuer_rev_reg"
    WEBHOOK_TOPIC = "revocation_registry"
    LOG_STATE_FLAG = "debug.revocation"
    CACHE_ENABLED = False
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
    STATE_PUBLISHED = "published"  # definition published
    STATE_STAGED = "staged"
    STATE_ACTIVE = "active"  # first entry published
    STATE_FULL = "full"

    def __init__(
        self,
        *,
        record_id: str = None,
        state: str = None,
        cred_def_id: str = None,
        error_msg: str = None,
        issuer_did: str = None,
        max_cred_num: int = None,
        revoc_def_type: str = None,
        revoc_reg_id: str = None,
        revoc_reg_def: dict = None,
        revoc_reg_entry: dict = None,
        tag: str = None,
        tails_hash: str = None,
        tails_local_path: str = None,
        tails_public_uri: str = None,
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
        self.revoc_reg_def = revoc_reg_def
        self.revoc_reg_entry = revoc_reg_entry
        self.tag = tag
        self.tails_hash = tails_hash
        self.tails_local_path = tails_local_path
        self.tails_public_uri = tails_public_uri
        self.pending_pub = (
            sorted(list(set(pending_pub))) if pending_pub else []
        )  # order for eq comparison between instances

    @property
    def record_id(self) -> str:
        """Accessor for the record ID."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Accessor for JSON value properties of this revocation registry record."""
        return {
            prop: getattr(self, prop)
            for prop in (
                "error_msg",
                "max_cred_num",
                "revoc_reg_def",
                "revoc_reg_entry",
                "tag",
                "tails_hash",
                "tails_public_uri",
                "tails_local_path",
                "pending_pub",
            )
        }

    def _check_url(self, url) -> None:
        parsed = urlparse(url)
        if not (parsed.scheme and parsed.netloc and parsed.path):
            raise RevocationError("URI {} is not a valid URL".format(url))

    async def generate_registry(self, context: InjectionContext):
        """Create the credential registry definition and tails file."""
        if not self.tag:
            self.tag = self._id or str(uuid.uuid4())

        if self.state != IssuerRevRegRecord.STATE_INIT:
            raise RevocationError(
                "Revocation registry {} in state {}: cannot generate".format(
                    self.revoc_reg_id, self.state
                )
            )

        issuer: BaseIssuer = await context.inject(BaseIssuer)
        tails_hopper_dir = indy_client_dir(join("tails", ".hopper"), create=True)

        LOGGER.debug("create revocation registry with size:", self.max_cred_num)

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
        except IssuerError as err:
            raise RevocationError() from err

        self.revoc_reg_id = revoc_reg_id
        self.revoc_reg_def = json.loads(revoc_reg_def_json)
        self.revoc_reg_entry = json.loads(revoc_reg_entry_json)
        self.state = IssuerRevRegRecord.STATE_GENERATED
        self.tails_hash = self.revoc_reg_def["value"]["tailsHash"]

        tails_dir = indy_client_dir(join("tails", self.revoc_reg_id), create=True)
        tails_path = join(tails_dir, self.tails_hash)
        move(join(tails_hopper_dir, self.tails_hash), tails_path)
        self.tails_local_path = tails_path

        await self.save(context, reason="Generated registry")

    async def set_tails_file_public_uri(
        self, context: InjectionContext, tails_file_uri: str
    ):
        """Update tails file's publicly accessible URI."""
        if not (
            self.revoc_reg_def
            and self.revoc_reg_def.get("value", {}).get("tailsLocation")
        ):
            raise RevocationError("Revocation registry undefined")

        self._check_url(tails_file_uri)

        self.tails_public_uri = tails_file_uri
        self.revoc_reg_def["value"]["tailsLocation"] = tails_file_uri
        await self.save(context, reason="Set tails file public URI")

    async def stage_pending_registry_definition(
        self, context: InjectionContext,
    ):
        """Prepare registry definition for future use."""
        await shield(self.generate_registry(context))
        tails_base_url = context.settings.get("tails_server_base_url")
        await self.set_tails_file_public_uri(
            context, f"{tails_base_url}/{self.revoc_reg_id}",
        )
        await self.publish_registry_definition(context)

        tails_server: BaseTailsServer = await context.inject(BaseTailsServer)
        await tails_server.upload_tails_file(
            context, self.revoc_reg_id, self.tails_local_path,
        )

    async def publish_registry_definition(self, context: InjectionContext):
        """Send the revocation registry definition to the ledger."""
        if not (self.revoc_reg_def and self.issuer_did):
            raise RevocationError(f"Revocation registry {self.revoc_reg_id} undefined")

        self._check_url(self.tails_public_uri)

        if self.state not in (
            IssuerRevRegRecord.STATE_GENERATED,
            IssuerRevRegRecord.STATE_STAGED,
        ):
            raise RevocationError(
                "Revocation registry {} in state {}: cannot publish definition".format(
                    self.revoc_reg_id, self.state
                )
            )

        ledger: BaseLedger = await context.inject(BaseLedger)
        async with ledger:
            await ledger.send_revoc_reg_def(self.revoc_reg_def, self.issuer_did)
        self.state = IssuerRevRegRecord.STATE_PUBLISHED
        await self.save(context, reason="Published revocation registry definition")

    async def publish_registry_entry(self, context: InjectionContext):
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
            IssuerRevRegRecord.STATE_PUBLISHED,
            IssuerRevRegRecord.STATE_ACTIVE,
            IssuerRevRegRecord.STATE_STAGED,
            IssuerRevRegRecord.STATE_FULL,  # can still publish revocation deltas
        ):
            raise RevocationError(
                "Revocation registry {} in state {}: cannot publish entry".format(
                    self.revoc_reg_id, self.state
                )
            )

        ledger: BaseLedger = await context.inject(BaseLedger)
        async with ledger:
            await ledger.send_revoc_reg_entry(
                self.revoc_reg_id,
                self.revoc_def_type,
                self.revoc_reg_entry,
                self.issuer_did,
            )
        if self.state in (
            IssuerRevRegRecord.STATE_PUBLISHED,
            IssuerRevRegRecord.STATE_STAGED,
        ):  # initial entry activates
            self.state = IssuerRevRegRecord.STATE_ACTIVE
            await self.save(
                context, reason="Published initial revocation registry entry"
            )

    async def mark_pending(self, context: InjectionContext, cred_rev_id: str) -> None:
        """Mark a credential revocation id as revoked pending publication to ledger.

        Args:
            context: The injection context to use
            cred_rev_id: The credential revocation identifier for credential to revoke
        """
        if cred_rev_id not in self.pending_pub:
            self.pending_pub.append(cred_rev_id)
            self.pending_pub.sort()

        await self.save(context, reason="Marked pending revocation")

    async def clear_pending(
        self, context: InjectionContext, cred_rev_ids: Sequence[str] = None
    ) -> None:
        """Clear pending revocations and save any resulting record change.

        Args:
            context: The injection context to use
            cred_rev_ids: Credential revocation identifiers to clear; default all
        """
        if self.pending_pub:
            if cred_rev_ids:
                self.pending_pub = [
                    r for r in self.pending_pub if r not in cred_rev_ids
                ]
            else:
                self.pending_pub.clear()
            await self.save(context, reason="Cleared pending revocations")

    async def get_registry(self) -> RevocationRegistry:
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
        cls, context: InjectionContext, cred_def_id: str, state: str = None
    ) -> Sequence["IssuerRevRegRecord"]:
        """Retrieve revocation registry records by credential definition ID.

        Args:
            context: The injection context to use
            cred_def_id: The credential definition ID to filter by
            state: A state value to filter by
        """
        tag_filter = {"cred_def_id": cred_def_id}
        if state:
            tag_filter["state"] = state
        return await cls.query(context, tag_filter)

    @classmethod
    async def query_by_pending(
        cls, context: InjectionContext
    ) -> Sequence["IssuerRevRegRecord"]:
        """Retrieve revocation records with revocations pending.

        Args:
            context: The injection context to use
        """
        return await cls.query(
            context=context,
            tag_filter=None,
            post_filter_positive=None,
            post_filter_negative={"pending_pub": []},
        )

    @classmethod
    async def retrieve_by_revoc_reg_id(
        cls, context: InjectionContext, revoc_reg_id: str
    ) -> Sequence["IssuerRevRegRecord"]:
        """Retrieve a revocation registry record by revocation registry ID.

        Args:
            context: The injection context to use
            revoc_reg_id: The revocation registry ID
        """
        tag_filter = {"revoc_reg_id": revoc_reg_id}
        return await cls.retrieve_by_tag_filter(context, tag_filter)

    async def mark_full(self, context: InjectionContext):
        """Change the registry state to full."""
        self.state = IssuerRevRegRecord.STATE_FULL
        await self.save(context, reason="Marked full")

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class IssuerRevRegRecordSchema(BaseRecordSchema):
    """Schema to allow serialization/deserialization of revocation registry records."""

    class Meta:
        """IssuerRevRegRecordSchema metadata."""

        model_class = IssuerRevRegRecord

    record_id = fields.Str(
        required=False,
        description="Issuer revocation registry record identifier",
        example=UUIDFour.EXAMPLE,
    )
    state = fields.Str(
        required=False,
        description="Issue revocation registry record state",
        example=IssuerRevRegRecord.STATE_ACTIVE,
    )
    cred_def_id = fields.Str(
        required=False,
        description="Credential definition identifier",
        **INDY_CRED_DEF_ID,
    )
    error_msg = fields.Str(
        required=False,
        description="Error message",
        example="Revocation registry undefined",
    )
    issuer_did = fields.Str(required=False, description="Issuer DID", **INDY_DID)
    max_cred_num = fields.Int(
        required=False,
        description="Maximum number of credentials for revocation registry",
        example=1000,
    )
    revoc_def_type = fields.Str(
        required=False,
        description="Revocation registry type (specify CL_ACCUM)",
        example="CL_ACCUM",
        validate=validate.Equal("CL_ACCUM"),
    )
    revoc_reg_id = fields.Str(
        required=False, description="Revocation registry identifier", **INDY_REV_REG_ID
    )
    revoc_reg_def = fields.Dict(
        required=False, description="Revocation registry definition"
    )
    revoc_reg_entry = fields.Dict(
        required=False, description="Revocation registry entry"
    )
    tag = fields.Str(
        required=False, description="Tag within issuer revocation registry identifier"
    )
    tails_hash = fields.Str(
        required=False, description="Tails hash", **BASE58_SHA256_HASH
    )
    tails_public_uri = fields.Str(
        required=False, description="Public URI for tails file"
    )
    tails_local_path = fields.Str(
        required=False, description="Local path to tails file"
    )
    pending_pub = fields.List(
        fields.Str(example="23"),
        description=(
            "Credential revocation identifier for credential "
            "revoked and pending publication to ledger"
        ),
        required=False,
    )
