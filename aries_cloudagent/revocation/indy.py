"""Indy revocation registry management."""

import json
import tempfile
import uuid
from typing import Sequence

import indy.anoncreds
import indy.blob_storage
import indy.ledger

from marshmallow import fields

from ..config.injection_context import InjectionContext
from ..core.error import BaseError
from ..ledger.base import BaseLedger
from ..messaging.models.base_record import BaseRecord, BaseRecordSchema
from ..utils.http import fetch, FetchError
from ..wallet.base import BaseWallet

DEFAULT_REGISTRY_SIZE = 100


class RevocationError(BaseError):
    """Base exception for revocation-related errors."""


class IndyRevocation:
    """Class for managing Indy credential revocation."""

    TEMP_DIR = None
    REGISTRY_CACHE = {}

    def __init__(self, context: InjectionContext):
        """Initialize the IndyRevocation instance."""
        self._context = context

    @classmethod
    def get_temp_dir(cls) -> str:
        """Accessor for the temp directory."""
        if not cls.TEMP_DIR:
            cls.TEMP_DIR = tempfile.TemporaryDirectory("revoc")
        return cls.TEMP_DIR.name

    async def init_issuer_registry(
        self,
        cred_def_id: str,
        issuer_did: str,
        in_advance: bool = True,
        max_cred_num: int = None,
        revoc_def_type: str = None,
        tag: str = None,
    ) -> "IssuerRevocationRecord":
        """Create a new revocation registry record for a credential definition."""
        record = IssuerRevocationRecord(
            cred_def_id=cred_def_id,
            issuer_did=issuer_did,
            issuance_type=IssuerRevocationRecord.ISSUANCE_BY_DEFAULT
            if in_advance
            else IssuerRevocationRecord.ISSUANCE_ON_DEMAND,
            max_cred_num=max_cred_num,
            revoc_def_type=revoc_def_type,
            tag=tag,
        )
        await record.save(self._context, reason="Init revocation registry")
        self.REGISTRY_CACHE[cred_def_id] = record.record_id
        return record

    async def get_active_issuer_revocation_record(
        self, cred_def_id: str, await_create: bool = False
    ) -> "IssuerRevocationRecord":
        """Return the current active registry for issuing a given credential definition.

        If no registry exists, then a new one will be created.

        Args:
            cred_def_id: ID of the base credential definition
            await_create: Wait for the registry and tails file to be created, if needed
        """
        # FIXME filter issuing registries by cred def, state (active or full), pick one
        if cred_def_id in self.REGISTRY_CACHE:
            registry = await IssuerRevocationRecord.retrieve_by_id(
                self._context, self.REGISTRY_CACHE[cred_def_id]
            )
            return registry

    async def get_issuer_revocation_record(
        self, revoc_reg_id: str
    ) -> "IssuerRevocationRecord":
        """Return the current active registry for issuing a given credential definition.

        If no registry exists, then a new one will be created.

        Args:
            cred_def_id: ID of the base credential definition
            await_create: Wait for the registry and tails file to be created, if needed
        """
        # FIXME handle exception
        return await IssuerRevocationRecord.retrieve_by_revoc_reg_id(
            self._context, revoc_reg_id
        )

    async def list_issuer_registries(self) -> Sequence["IssuerRevocationRecord"]:
        """List the current revocation registries."""
        # return list of records (need filters)

    async def get_ledger_registry(self, revoc_reg_id: str) -> "RevocationRegistry":
        """Get a revocation registry from the ledger, fetching as necessary."""
        ledger: BaseLedger = await self._context.inject(BaseLedger)
        revoc_reg_def = await ledger.get_revoc_reg_def(revoc_reg_id)
        # TODO apply caching here?
        return RevocationRegistry.from_definition(revoc_reg_def, True)


class RevocationRegistry:
    """Manage a revocation registry and tails file."""

    def __init__(
        self,
        registry_id: str = None,
        *,
        cred_def_id: str = None,
        issuer_did: str = None,
        max_creds: int = None,
        reg_def_type: str = None,
        tag: str = None,
        tails_local_path: str = None,
        tails_public_uri: str = None,
        tails_hash: str = None,
    ):
        """Initialize the revocation registry instance."""
        self._cred_def_id = cred_def_id
        self._issuer_did = issuer_did
        self._max_creds = max_creds
        self._reg_def_type = reg_def_type
        self._registry_id = registry_id
        self._tag = tag
        self._tails_local_path = tails_local_path
        self._tails_public_uri = tails_public_uri
        self._tails_hash = tails_hash

    @classmethod
    def from_definition(
        cls, revoc_reg_def: dict, public_def: bool
    ) -> "RevocationRegistry":
        """Initialize a revocation registry instance from a definition."""
        reg_id = revoc_reg_def.get("id")
        tails_location = revoc_reg_def["value"]["tailsLocation"]
        init = {
            "cred_def_id": revoc_reg_def["credDefId"],
            "reg_def_type": revoc_reg_def["regDefType"],
            "max_creds": revoc_reg_def["value"]["maxCredNum"],
            "tag": revoc_reg_def["tag"],
            "tails_hash": revoc_reg_def["value"]["tailsHash"],
        }
        if public_def:
            init["tails_local_path"] = tails_location
        else:
            init["tails_public_uri"] = tails_location
        # currently ignored - definition version, public keys
        return cls(reg_id, **init)

    @property
    def cred_def_id(self) -> str:
        """Accessor for the credential definition ID."""
        return self._cred_def_id

    @property
    def issuer_did(self) -> str:
        """Accessor for the issuer DID."""
        return self._issuer_did

    @property
    def max_creds(self) -> int:
        """Accessor for the maximum number of issued credentials."""
        return self._max_creds

    @property
    def reg_def_type(self) -> str:
        """Accessor for the revocation registry type."""
        return self._reg_def_type

    @property
    def registry_id(self) -> str:
        """Accessor for the revocation registry ID."""
        return self._registry_id

    @property
    def tag(self) -> str:
        """Accessor for the tag part of the revoc. reg. ID."""
        return self._tag

    @property
    def tails_hash(self) -> str:
        """Accessor for the tails file hash."""
        return self._tails_hash

    @property
    def tails_local_path(self) -> str:
        """Accessor for the tails file local path."""
        return self._tails_local_path

    @tails_local_path.setter
    def tails_local_path(self, new_path: str):
        """Setter for the tails file local path."""
        self._tails_local_path = new_path

    @property
    def tails_public_uri(self) -> str:
        """Accessor for the tails file public URI."""
        return self._tails_public_uri

    @tails_public_uri.setter
    def tails_public_uri(self, new_uri: str):
        """Setter for the tails file public URI."""
        self._tails_public_uri = new_uri

    async def create_tails_reader(self) -> int:
        """Get a handle for the blob_storage file reader."""
        if self._tails_local_path:
            tails_reader_config = json.dumps(
                {
                    "base_dir": IndyRevocation.get_temp_dir(),
                    "file": self._tails_local_path,
                }
            )
            return await indy.blob_storage.open_reader("default", tails_reader_config)

    async def retrieve_tails(self, target_dir: str) -> str:
        """Fetch the tails file from the public URI."""
        if self._tails_public_uri:
            try:
                tails = await fetch(self._tails_public_uri)
            except FetchError as e:
                raise RevocationError("Error retrieving tails file") from e
            with tempfile.mkstemp(suffix="tails", dir=target_dir, text=True) as tf:
                tf.write(tails)
                return tf.name

    def __repr__(self) -> str:
        """Return a human readable representation of this class."""
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))


class IssuerRevocationRecord(BaseRecord):
    """Class for managing local issuing revocation registries."""

    class Meta:
        """IssuerRevocationRecord metadata."""

        schema_class = "IssuerRevocationRecordSchema"

    RECORD_ID_NAME = "record_id"
    RECORD_TYPE = "issuer_revoc"
    LOG_STATE_FLAG = "debug.revocation"
    CACHE_ENABLED = False
    TAG_NAMES = {
        "cred_def_id",
        "issuance_type",
        "issuer_did",
        "revoc_def_type",
        "revoc_reg_id",
        "state",
    }

    ISSUANCE_BY_DEFAULT = "ISSUANCE_BY_DEFAULT"
    ISSUANCE_ON_DEMAND = "ISSUANCE_ON_DEMAND"

    REVOC_DEF_TYPE_CL = "CL_ACCUM"

    STATE_INIT = "init"
    STATE_GENERATED = "generated"
    STATE_PUBLISHED = "published"
    STATE_ACTIVE = "active"
    STATE_FULL = "full"

    def __init__(
        self,
        *,
        record_id: str = None,
        state: str = None,
        cred_def_id: str = None,
        error_msg: str = None,
        issuance_type: str = None,
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
        **kwargs,
    ):
        """Initialize the issuer revocation registry record."""
        super(IssuerRevocationRecord, self).__init__(
            record_id, state=state or self.STATE_INIT, **kwargs
        )
        self.cred_def_id = cred_def_id
        self.error_msg = error_msg
        self.issuance_type = issuance_type or self.ISSUANCE_BY_DEFAULT
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

    @property
    def record_id(self) -> str:
        """Accessor for the record ID."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value properties for this revocation record."""
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
                # FIXME - remove
                "tails_local_path",
            )
        }

    async def generate_registry(self, context: InjectionContext, base_dir: str):
        """Create the credential registry definition and tails file."""
        wallet = await context.inject(BaseWallet, required=False)
        if not wallet or wallet.WALLET_TYPE != "indy":
            raise RevocationError("Wallet type of 'indy' must be provided")
        if not self.tag:
            self.tag = self._id or str(uuid.uuid4())

        tails_writer_config = json.dumps({"base_dir": base_dir, "uri_pattern": ""})
        tails_writer = await indy.blob_storage.open_writer(
            "default", tails_writer_config
        )

        print("create with max cred num:", self.max_cred_num)

        (
            revoc_reg_id,
            revoc_reg_def_json,
            revoc_reg_entry_json,
        ) = await indy.anoncreds.issuer_create_and_store_revoc_reg(
            wallet.handle,
            self.issuer_did,
            self.revoc_def_type,
            self.tag,
            self.cred_def_id,
            json.dumps(
                {"max_cred_num": self.max_cred_num, "issuance_type": self.issuance_type}
            ),
            tails_writer,
        )

        self.revoc_reg_id = revoc_reg_id
        self.revoc_reg_def = json.loads(revoc_reg_def_json)
        self.revoc_reg_entry = json.loads(revoc_reg_entry_json)
        self.state = self.STATE_GENERATED
        self.tails_hash = self.revoc_reg_def["value"]["tailsHash"]
        self.tails_local_path = self.revoc_reg_def["value"]["tailsLocation"]
        await self.save(context, reason="Generated registry")

    async def publish_registry_definition(self, context: InjectionContext):
        """Send the revocation registry definition to the ledger."""
        ledger: BaseLedger = await context.inject(BaseLedger)
        await ledger.send_revoc_reg_def(self.revoc_reg_def, self.issuer_did)

    async def publish_registry_entry(self, context: InjectionContext):
        """Send a registry entry to the ledger."""
        ledger: BaseLedger = await context.inject(BaseLedger)
        await ledger.send_revoc_reg_entry(
            self.revoc_reg_id,
            self.revoc_def_type,
            self.revoc_reg_entry,
            self.issuer_did,
        )

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
    ) -> Sequence["IssuerRevocationRecord"]:
        """Retrieve a revocation record by credential definition ID.

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
    async def retrieve_by_revoc_reg_id(
        cls, context: InjectionContext, revoc_reg_id: str
    ) -> Sequence["IssuerRevocationRecord"]:
        """Retrieve a revocation record by revocation registry ID.

        Args:
            context: The injection context to use
            revoc_reg_id: The revocation registry ID
        """
        tag_filter = {"revoc_reg_id": revoc_reg_id}
        return await cls.retrieve_by_tag_filter(context, tag_filter)

    async def mark_full(self, context: InjectionContext):
        """Change the registry state to full."""
        self.state = self.STATE_FULL
        await self.save(context)


class IssuerRevocationRecordSchema(BaseRecordSchema):
    """Schema to allow serialization/deserialization of revocation records."""

    class Meta:
        """ConnectionRecordSchema metadata."""

        model_class = IssuerRevocationRecord

    record_id = fields.Str(required=False)
    cred_def_id = fields.Str(required=False)
    error_msg = fields.Str(required=False)
    issuance_type = fields.Str(required=False)
    issuer_did = fields.Str(required=False)
    max_cred_num = fields.Int(required=False)
    revoc_def_type = fields.Str(required=False)
    revoc_reg_id = fields.Str(required=False)
    revoc_reg_def = fields.Dict(required=False)
    revoc_reg_entry = fields.Dict(required=False)
    tag = fields.Str(required=False)
    tails_hash = fields.Str(required=False)
    tails_public_uri = fields.Str(required=False)
