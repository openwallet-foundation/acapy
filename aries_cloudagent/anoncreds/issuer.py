"""anoncreds-rs issuer implementation."""

import asyncio
import logging
from time import time
from typing import NamedTuple, Optional, Sequence, Tuple

from anoncreds import (
    AnoncredsError,
    Credential,
    CredentialDefinition,
    CredentialOffer,
    CredentialRevocationConfig,
    RevocationRegistryDefinition,
    RevocationRegistryDelta,
    RevocationStatusList,
    Schema,
)
from aries_askar import AskarError

from ..askar.profile import AskarProfile
from ..core.error import BaseError
from .base import AnonCredsSchemaAlreadyExists
from .models.anoncreds_cred_def import CredDef, CredDefResult, CredDefState
from .models.anoncreds_revocation import (
    RevRegDef,
    RevRegDefResult,
    RevRegDefState,
    RevList,
)
from .models.anoncreds_schema import AnonCredsSchema, SchemaResult, SchemaState
from .registry import AnonCredsRegistry
from .util import indy_client_dir

LOGGER = logging.getLogger(__name__)

DEFAULT_CRED_DEF_TAG = "default"
DEFAULT_SIGNATURE_TYPE = "CL"
CATEGORY_CRED_DEF = "credential_def"
CATEGORY_CRED_DEF_PRIVATE = "credential_def_private"
CATEGORY_CRED_DEF_KEY_PROOF = "credential_def_key_proof"
CATEGORY_SCHEMA = "schema"
CATEGORY_REV_LIST = "revocation_list"
CATEGORY_REV_REG_INFO = "revocation_reg_info"
CATEGORY_REV_REG_DEF = "revocation_reg_def"
CATEGORY_REV_REG_DEF_PRIVATE = "revocation_reg_def_private"
CATEGORY_REV_REG_ISSUER = "revocation_reg_def_issuer"


class AnonCredsIssuerError(BaseError):
    """Generic issuer error."""


class AnonCredsIssuerRevocationRegistryFullError(AnonCredsIssuerError):
    """Revocation registry is full when issuing a new credential."""


class RevokeResult(NamedTuple):
    prev: Optional[RevocationStatusList] = None
    curr: Optional[RevocationStatusList] = None
    failed: Optional[Sequence[str]] = None


class AnonCredsIssuer:
    """AnonCreds issuer class."""

    def __init__(self, profile: AskarProfile):
        """
        Initialize an IndyCredxIssuer instance.

        Args:
            profile: The active profile instance

        """
        self._profile = profile

    @property
    def profile(self) -> AskarProfile:
        """Accessor for the profile instance."""
        return self._profile

    async def _update_entry_state(self, category: str, name: str, state: str):
        """Update the state tag of an entry in a given category."""
        try:
            async with self._profile.transaction() as txn:
                entry = await txn.handle.fetch(
                    category,
                    name,
                    for_update=True,
                )
                if not entry:
                    raise AnonCredsIssuerError(
                        f"{category} with id {name} could not be found"
                    )

                entry.tags["state"] = state
                await txn.handle.replace(
                    CATEGORY_SCHEMA,
                    name,
                    tags=entry.tags,
                )
        except AskarError as err:
            raise AnonCredsIssuerError(f"Error marking {category} as {state}") from err

    async def _store_schema(
        self,
        schema_id: str,
        schema: AnonCredsSchema,
        state: str,
    ):
        """Store schema after reaching finished state."""
        try:
            async with self._profile.session() as session:
                await session.handle.insert(
                    CATEGORY_SCHEMA,
                    schema_id,
                    schema.to_json(),
                    {
                        "name": schema.name,
                        "version": schema.version,
                        "issuer_id": schema.issuer_id,
                        "state": state,
                    },
                )
        except AskarError as err:
            raise AnonCredsIssuerError("Error storing schema") from err

    async def create_and_register_schema(
        self,
        issuer_id: str,
        name: str,
        version: str,
        attr_names: Sequence[str],
        options: Optional[dict] = None,
    ) -> SchemaResult:
        """
        Create a new credential schema and store it in the wallet.

        Args:
            issuer_id: the DID issuing the credential definition
            name: the schema name
            version: the schema version
            attr_names: a sequence of schema attribute names

        Returns:
            A SchemaResult instance

        """
        # Check if record of a similar schema already exists in our records
        async with self._profile.session() as session:
            # TODO scan?
            schemas = await session.handle.fetch_all(
                CATEGORY_SCHEMA,
                {
                    "name": name,
                    "version": version,
                    "issuer_id": issuer_id,
                },
                limit=1,
            )
            if schemas:
                raise AnonCredsSchemaAlreadyExists(
                    f"Schema with {name}: {version} " f"already exists for {issuer_id}"
                )

        # TODO Do we even need to create the native object here?
        schema = Schema.create(name, version, issuer_id, attr_names)
        try:
            anoncreds_registry = self._profile.inject(AnonCredsRegistry)

            schema_result = await anoncreds_registry.register_schema(
                self.profile,
                AnonCredsSchema.from_native(schema),
                options,
            )

            await self._store_schema(
                schema_result.schema_state.schema_id,
                schema_result.schema_state.schema,
                state=schema_result.schema_state.state,
            )

            return schema_result

        except AnonCredsSchemaAlreadyExists as err:
            # If we find that we've previously written a schema that looks like
            # this one before but that schema is not in our wallet, add it to
            # the wallet so we can return from our get schema calls
            if err.schema_id and err.schema:
                await self._store_schema(
                    err.schema_id, err.schema, SchemaState.STATE_FINISHED
                )
                raise AnonCredsIssuerError(
                    "Schema already exists but was not in wallet; stored in wallet"
                ) from err
            raise
        except AnoncredsError as err:
            raise AnonCredsIssuerError("Error creating schema") from err

    async def update_schema_state(self, schema_id: str, state: str):
        """Update the state of the stored schema."""
        await self._update_entry_state(CATEGORY_SCHEMA, schema_id, state)

    async def finish_schema(self, schema_id: str):
        """Mark a schema as finished."""
        await self.update_schema_state(schema_id, SchemaState.STATE_FINISHED)

    async def get_created_schemas(
        self,
        name: Optional[str] = None,
        version: Optional[str] = None,
        issuer_id: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Sequence[str]:
        """Retrieve IDs of schemas previously created."""
        async with self._profile.session() as session:
            # TODO limit? scan?
            schemas = await session.handle.fetch_all(
                CATEGORY_SCHEMA,
                {
                    key: value
                    for key, value in {
                        "name": name,
                        "version": version,
                        "issuer_id": issuer_id,
                        "state": state,
                    }.items()
                    if value is not None
                },
            )
        # entry.name was stored as the schema's ID
        return [entry.name for entry in schemas]

    @staticmethod
    def make_credential_definition_id(
        origin_did: str, schema: dict, signature_type: str = None, tag: str = None
    ) -> str:
        """Derive the ID for a credential definition."""
        signature_type = signature_type or DEFAULT_SIGNATURE_TYPE
        tag = tag or DEFAULT_CRED_DEF_TAG
        return f"{origin_did}:3:{signature_type}:{str(schema['seqNo'])}:{tag}"

    async def credential_definition_in_wallet(
        self, credential_definition_id: str
    ) -> bool:
        """
        Check whether a given credential definition ID is present in the wallet.

        Args:
            credential_definition_id: The credential definition ID to check
        """
        try:
            async with self._profile.session() as session:
                return (
                    await session.handle.fetch(
                        CATEGORY_CRED_DEF_PRIVATE, credential_definition_id
                    )
                ) is not None
        except AskarError as err:
            raise AnonCredsIssuerError(
                "Error checking for credential definition"
            ) from err

    async def create_and_register_credential_definition(
        self,
        issuer_id: str,
        schema_id: str,
        tag: Optional[str] = None,
        signature_type: Optional[str] = None,
        options: Optional[dict] = None,
    ) -> CredDefResult:
        """
        Create a new credential definition and store it in the wallet.

        Args:
            origin_did: the DID issuing the credential definition
            schema_json: the schema used as a basis
            signature_type: the credential definition signature type (default 'CL')
            tag: the credential definition tag
            support_revocation: whether to enable revocation for this credential def

        Returns:
            A tuple of the credential definition ID and JSON

        """
        anoncreds_registry = self._profile.inject(AnonCredsRegistry)
        schema_result = await anoncreds_registry.get_schema(self.profile, schema_id)

        options = options or {}
        support_revocation = options.get("support_revocation", False)

        try:
            # Create the cred def
            (
                cred_def,
                cred_def_private,
                key_proof,
            ) = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: CredentialDefinition.create(
                    schema_id,
                    schema_result.schema.serialize(),
                    issuer_id,
                    tag or DEFAULT_CRED_DEF_TAG,
                    signature_type or DEFAULT_SIGNATURE_TYPE,
                    support_revocation=support_revocation,
                ),
            )
            cred_def_json = cred_def.to_json()

            # Register the cred def
            result = await anoncreds_registry.register_credential_definition(
                self.profile,
                schema_result,
                CredDef.from_native(cred_def),
                options,
            )
        except AnoncredsError as err:
            raise AnonCredsIssuerError("Error creating credential definition") from err

        # Store the cred def and it's components
        try:
            cred_def_id = result.credential_definition_state.credential_definition_id
            async with self._profile.transaction() as txn:
                await txn.handle.insert(
                    CATEGORY_CRED_DEF,
                    cred_def_id,
                    cred_def_json,
                    # Note: Indy-SDK uses a separate SchemaId record for this
                    tags={
                        "schema_id": schema_id,
                        "schema_issuer_id": schema_result.schema.issuer_id,
                        "issuer_id": issuer_id,
                        "schema_name": schema_result.schema.name,
                        "schema_version": schema_result.schema.version,
                        "state": result.credential_definition_state.state,
                        "epoch": str(int(time())),
                    },
                )
                await txn.handle.insert(
                    CATEGORY_CRED_DEF_PRIVATE,
                    cred_def_id,
                    cred_def_private.to_json_buffer(),
                )
                await txn.handle.insert(
                    CATEGORY_CRED_DEF_KEY_PROOF, cred_def_id, key_proof.to_json_buffer()
                )
                await txn.commit()
        except AskarError as err:
            raise AnonCredsIssuerError("Error storing credential definition") from err

        return result

    async def update_cred_def_state(self, cred_def_id: str, state: str):
        """Update the state of a cred def."""
        await self._update_entry_state(CATEGORY_CRED_DEF, cred_def_id, state)

    async def finish_cred_def(self, cred_def_id: str):
        """Finish a cred def."""
        await self.update_cred_def_state(cred_def_id, CredDefState.STATE_FINISHED)

    async def get_created_credential_definitions(
        self,
        issuer_id: Optional[str] = None,
        schema_issuer_id: Optional[str] = None,
        schema_id: Optional[str] = None,
        schema_name: Optional[str] = None,
        schema_version: Optional[str] = None,
        state: Optional[str] = None,
        epoch: Optional[str] = None,
    ) -> Sequence[str]:
        """Retrieve IDs of credential definitions previously created."""
        async with self._profile.session() as session:
            # TODO limit? scan?
            credential_definition_entries = await session.handle.fetch_all(
                CATEGORY_CRED_DEF,
                {
                    key: value
                    for key, value in {
                        "issuer_id": issuer_id,
                        "schema_issuer_id": schema_issuer_id,
                        "schema_id": schema_id,
                        "schema_name": schema_name,
                        "schema_version": schema_version,
                        "state": state,
                        "epoch": epoch,
                    }.items()
                    if value is not None
                },
            )
        return [entry.name for entry in credential_definition_entries]

    async def match_created_credential_definitions(
        self,
        cred_def_id: Optional[str] = None,
        issuer_id: Optional[str] = None,
        schema_issuer_id: Optional[str] = None,
        schema_id: Optional[str] = None,
        schema_name: Optional[str] = None,
        schema_version: Optional[str] = None,
        state: Optional[str] = None,
        epoch: Optional[str] = None,
    ) -> Optional[str]:
        """Return cred def id of most recent matching cred def."""
        async with self._profile.session() as session:
            # TODO limit? scan?
            if cred_def_id:
                cred_def_entry = await session.handle.fetch(
                    CATEGORY_CRED_DEF, cred_def_id
                )
            else:
                credential_definition_entries = await session.handle.fetch_all(
                    CATEGORY_CRED_DEF,
                    {
                        key: value
                        for key, value in {
                            "issuer_id": issuer_id,
                            "schema_issuer_id": schema_issuer_id,
                            "schema_id": schema_id,
                            "schema_name": schema_name,
                            "schema_version": schema_version,
                            "state": state,
                            "epoch": epoch,
                        }.items()
                        if value is not None
                    },
                )
                cred_def_entry = max(
                    [entry for entry in credential_definition_entries],
                    key=lambda r: int(r.tags["epoch"]),
                )

        if cred_def_entry:
            return cred_def_entry.name

        return None

    async def cred_def_supports_revocation(self, cred_def_id: str) -> bool:
        """Return whether a credential definition supports revocation."""
        anoncreds_registry = self.profile.inject(AnonCredsRegistry)
        cred_def_result = await anoncreds_registry.get_credential_definition(
            self.profile, cred_def_id
        )
        return cred_def_result.credential_definition.value.revocation is not None

    async def create_and_register_revocation_registry_definition(
        self,
        issuer_id: str,
        cred_def_id: str,
        registry_type: str,
        tag: str,
        max_cred_num: int,
        options: Optional[dict] = None,
    ) -> RevRegDefResult:
        """
        Create a new revocation registry and store it in the wallet.

        Args:
            origin_did: the DID issuing the revocation registry
            cred_def_id: the identifier of the related credential definition
            revoc_def_type: the revocation registry type (default CL_ACCUM)
            tag: the unique revocation registry tag
            max_cred_num: the number of credentials supported in the registry
            tails_base_path: where to store the tails file
            issuance_type: optionally override the issuance type

        Returns:
            A tuple of the revocation registry ID, JSON, and entry JSON

        """
        try:
            async with self._profile.session() as session:
                cred_def = await session.handle.fetch(CATEGORY_CRED_DEF, cred_def_id)
        except AskarError as err:
            raise AnonCredsIssuerError(
                "Error retrieving credential definition"
            ) from err

        if not cred_def:
            raise AnonCredsIssuerError(
                "Credential definition not found for revocation registry"
            )

        tails_dir = indy_client_dir("tails", create=True)

        try:
            (
                rev_reg_def,
                rev_reg_def_private,
            ) = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: RevocationRegistryDefinition.create(
                    cred_def_id,
                    cred_def.raw_value,
                    issuer_id,
                    tag,
                    registry_type,
                    max_cred_num,
                    tails_dir_path=tails_dir,
                ),
            )
            # TODO Move tails file to more human friendly folder structure?
        except AnoncredsError as err:
            raise AnonCredsIssuerError("Error creating revocation registry") from err

        rev_reg_def_json = rev_reg_def.to_json()

        anoncreds_registry = self.profile.inject(AnonCredsRegistry)
        result = await anoncreds_registry.register_revocation_registry_definition(
            self.profile, RevRegDef.from_native(rev_reg_def), options
        )

        rev_reg_def_id = result.rev_reg_def_id

        try:
            async with self._profile.transaction() as txn:
                await txn.handle.insert(
                    CATEGORY_REV_REG_INFO,
                    rev_reg_def_id,
                    value_json={"curr_id": 0, "used_ids": []},
                )
                await txn.handle.insert(
                    CATEGORY_REV_REG_DEF,
                    rev_reg_def_id,
                    rev_reg_def_json,
                    tags={"cred_def_id": cred_def_id},
                )
                await txn.handle.insert(
                    CATEGORY_REV_REG_DEF_PRIVATE,
                    rev_reg_def_id,
                    rev_reg_def_private.to_json_buffer(),
                )
                await txn.commit()
        except AskarError as err:
            raise AnonCredsIssuerError("Error saving new revocation registry") from err

        return result

    async def update_revocation_registry_definition_state(
        self, rev_reg_def_id: str, state: str
    ):
        """Update the state of a rev reg def."""
        await self._update_entry_state(CATEGORY_REV_REG_DEF, rev_reg_def_id, state)

    async def finish_revocation_registry_definition(self, rev_reg_def_id: str):
        """Mark a rev reg def as finished."""
        await self.update_revocation_registry_definition_state(
            rev_reg_def_id, RevRegDefState.STATE_FINISHED
        )

    async def get_created_revocation_registry_definitions(
        self,
        cred_def_id: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Sequence[str]:
        """Retrieve IDs of rev reg defs previously created."""
        async with self._profile.session() as session:
            # TODO limit? scan?
            rev_reg_defs = await session.handle.fetch_all(
                CATEGORY_REV_REG_DEF,
                {
                    key: value
                    for key, value in {
                        "cred_def_id": cred_def_id,
                        "state": state,
                    }.items()
                    if value is not None
                },
            )
        # entry.name was stored as the credential_definition's ID
        return [entry.name for entry in rev_reg_defs]

    async def create_and_register_revocation_list(
        self, rev_reg_def_id: str, options: Optional[dict] = None
    ):
        """Create and register a revocation list."""
        try:
            async with self._profile.session() as session:
                rev_reg_def_entry = await session.handle.fetch(
                    CATEGORY_REV_REG_DEF, rev_reg_def_id
                )
        except AskarError as err:
            raise AnonCredsIssuerError(
                "Error retrieving credential definition"
            ) from err

        if not rev_reg_def_entry:
            raise AnonCredsIssuerError(
                f"Revocation registry definition not found for id {rev_reg_def_id}"
            )

        rev_reg_def = RevRegDef.deserialize(rev_reg_def_entry.value_json)

        rev_list = RevocationStatusList.create(
            rev_reg_def_id,
            rev_reg_def_entry.raw_value,
            rev_reg_def.issuer_id,
        )

        anoncreds_registry = self.profile.inject(AnonCredsRegistry)
        result = await anoncreds_registry.register_revocation_list(
            self.profile, rev_reg_def, RevList.from_native(rev_list), options
        )

        try:
            async with self._profile.session() as session:
                await session.handle.insert(
                    CATEGORY_REV_LIST,
                    rev_reg_def_id,
                    result.revocation_list_state.revocation_list.to_json(),
                )
        except AskarError as err:
            raise AnonCredsIssuerError("Error saving new revocation registry") from err

        return result

    async def create_credential_offer(self, credential_definition_id: str) -> str:
        """
        Create a credential offer for the given credential definition id.

        Args:
            credential_definition_id: The credential definition to create an offer for

        Returns:
            The new credential offer

        """
        try:
            async with self._profile.session() as session:
                cred_def = await session.handle.fetch(
                    CATEGORY_CRED_DEF, credential_definition_id
                )
                key_proof = await session.handle.fetch(
                    CATEGORY_CRED_DEF_KEY_PROOF, credential_definition_id
                )
        except AskarError as err:
            raise AnonCredsIssuerError(
                "Error retrieving credential definition"
            ) from err
        if not cred_def or not key_proof:
            raise AnonCredsIssuerError(
                "Credential definition not found for credential offer"
            )
        try:
            # The tag holds the full name of the schema,
            # as opposed to just the sequence number
            schema_id = cred_def.tags.get("schema_id")
            cred_def = CredentialDefinition.load(cred_def.raw_value)

            credential_offer = CredentialOffer.create(
                schema_id or cred_def.schema_id,
                credential_definition_id,
                key_proof.raw_value,
            )
        except AnoncredsError as err:
            raise AnonCredsIssuerError("Error creating credential offer") from err

        return credential_offer.to_json()

    async def create_credential(
        self,
        schema_id: str,
        credential_offer: dict,
        credential_request: dict,
        credential_values: dict,
        revoc_reg_id: Optional[str] = None,
        tails_file_path: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Create a credential.

        Args
            schema_id: Schema ID to create credential for
            credential_offer: Credential Offer to create credential for
            credential_request: Credential request to create credential for
            credential_values: Values to go in credential
            revoc_reg_id: ID of the revocation registry
            tails_file_path: The location of the tails file

        Returns:
            A tuple of created credential and revocation id

        """
        anoncreds_registry = self.profile.inject(AnonCredsRegistry)
        schema_result = await anoncreds_registry.get_schema(self.profile, schema_id)
        credential_definition_id = credential_offer["cred_def_id"]
        try:
            async with self._profile.session() as session:
                cred_def = await session.handle.fetch(
                    CATEGORY_CRED_DEF, credential_definition_id
                )
                cred_def_private = await session.handle.fetch(
                    CATEGORY_CRED_DEF_PRIVATE, credential_definition_id
                )
        except AskarError as err:
            raise AnonCredsIssuerError(
                "Error retrieving credential definition"
            ) from err
        if not cred_def or not cred_def_private:
            raise AnonCredsIssuerError(
                "Credential definition not found for credential issuance"
            )

        raw_values = {}
        schema_attributes = schema_result.schema.attr_names
        for attribute in schema_attributes:
            # Ensure every attribute present in schema to be set.
            # Extraneous attribute names are ignored.
            try:
                credential_value = credential_values[attribute]
            except KeyError:
                raise AnonCredsIssuerError(
                    "Provided credential values are missing a value "
                    f"for the schema attribute '{attribute}'"
                )

            raw_values[attribute] = str(credential_value)

        if revoc_reg_id:
            try:
                async with self._profile.transaction() as txn:
                    rev_list = await txn.handle.fetch(CATEGORY_REV_LIST, revoc_reg_id)
                    rev_reg_info = await txn.handle.fetch(
                        CATEGORY_REV_REG_INFO, revoc_reg_id, for_update=True
                    )
                    rev_reg_def = await txn.handle.fetch(
                        CATEGORY_REV_REG_DEF, revoc_reg_id
                    )
                    rev_key = await txn.handle.fetch(
                        CATEGORY_REV_REG_DEF_PRIVATE, revoc_reg_id
                    )
                    if not rev_list:
                        raise AnonCredsIssuerError("Revocation registry not found")
                    if not rev_reg_info:
                        raise AnonCredsIssuerError(
                            "Revocation registry metadata not found"
                        )
                    if not rev_reg_def:
                        raise AnonCredsIssuerError(
                            "Revocation registry definition not found"
                        )
                    if not rev_key:
                        raise AnonCredsIssuerError(
                            "Revocation registry definition private data not found"
                        )
                    # NOTE: we increment the index ahead of time to keep the
                    # transaction short. The revocation registry itself will NOT
                    # be updated because we always use ISSUANCE_BY_DEFAULT.
                    # If something goes wrong later, the index will be skipped.
                    # FIXME - double check issuance type in case of upgraded wallet?
                    rev_info = rev_reg_info.value_json
                    rev_reg_index = rev_info["curr_id"] + 1
                    try:
                        rev_reg_def = RevocationRegistryDefinition.load(
                            rev_reg_def.raw_value
                        )
                        rev_list = RevocationStatusList.load(rev_list.raw_value)
                    except AnoncredsError as err:
                        raise AnonCredsIssuerError(
                            "Error loading revocation registry definition"
                        ) from err
                    if rev_reg_index > rev_reg_def.max_cred_num:
                        raise AnonCredsIssuerRevocationRegistryFullError(
                            "Revocation registry is full"
                        )
                    rev_info["curr_id"] = rev_reg_index
                    await txn.handle.replace(
                        CATEGORY_REV_REG_INFO, revoc_reg_id, value_json=rev_info
                    )
                    await txn.commit()
            except AskarError as err:
                raise AnonCredsIssuerError(
                    "Error updating revocation registry index"
                ) from err

            revoc = CredentialRevocationConfig(
                rev_reg_def,
                rev_key.raw_value,
                rev_reg_index,
                tails_file_path,
            )
            credential_revocation_id = str(rev_reg_index)
        else:
            revoc = None
            credential_revocation_id = None
            rev_list = None

        try:
            credential = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: Credential.create(
                    cred_def.raw_value,
                    cred_def_private.raw_value,
                    credential_offer,
                    credential_request,
                    raw_values,
                    None,
                    revoc_reg_id,
                    rev_list,
                    revoc,
                ),
            )
        except AnoncredsError as err:
            raise AnonCredsIssuerError("Error creating credential") from err

        return credential.to_json(), credential_revocation_id

    async def revoke_credentials(
        self,
        revoc_reg_id: str,
        tails_file_path: str,
        cred_revoc_ids: Sequence[str],
    ) -> RevokeResult:
        """
        Revoke a set of credentials in a revocation registry.

        Args:
            revoc_reg_id: ID of the revocation registry
            tails_file_path: path to the local tails file
            cred_revoc_ids: sequences of credential indexes in the revocation registry

        Returns:
            Tuple with the update revocation list, list of cred rev ids not revoked

        """

        # TODO This method should return the old list, the new list,
        # and the list of changed indices
        prev_list = None
        updated_list = None
        failed_crids = set()
        max_attempt = 5
        attempt = 0

        while True:
            attempt += 1
            if attempt >= max_attempt:
                raise AnonCredsIssuerError(
                    "Repeated conflict attempting to update registry"
                )
            try:
                async with self._profile.session() as session:
                    rev_reg_def_entry = await session.handle.fetch(
                        CATEGORY_REV_REG_DEF, revoc_reg_id
                    )
                    rev_list_entry = await session.handle.fetch(
                        CATEGORY_REV_LIST, revoc_reg_id
                    )
                    rev_reg_info = await session.handle.fetch(
                        CATEGORY_REV_REG_INFO, revoc_reg_id
                    )
                if not rev_reg_def_entry:
                    raise AnonCredsIssuerError(
                        "Revocation registry definition not found"
                    )
                if not rev_list_entry:
                    raise AnonCredsIssuerError("Revocation registry not found")
                if not rev_reg_info:
                    raise AnonCredsIssuerError("Revocation registry metadata not found")
            except AskarError as err:
                raise AnonCredsIssuerError(
                    "Error retrieving revocation registry"
                ) from err

            try:
                rev_reg_def = RevocationRegistryDefinition.load(
                    rev_reg_def_entry.raw_value
                )
            except AnoncredsError as err:
                raise AnonCredsIssuerError(
                    "Error loading revocation registry definition"
                ) from err

            rev_crids = set()
            failed_crids = set()
            max_cred_num = rev_reg_def.max_cred_num
            rev_info = rev_reg_info.value_json
            used_ids = set(rev_info.get("used_ids") or [])

            for rev_id in cred_revoc_ids:
                rev_id = int(rev_id)
                if rev_id < 1 or rev_id > max_cred_num:
                    LOGGER.error(
                        "Skipping requested credential revocation"
                        "on rev reg id %s, cred rev id=%s not in range",
                        revoc_reg_id,
                        rev_id,
                    )
                    failed_crids.add(rev_id)
                elif rev_id > rev_info["curr_id"]:
                    LOGGER.warn(
                        "Skipping requested credential revocation"
                        "on rev reg id %s, cred rev id=%s not yet issued",
                        revoc_reg_id,
                        rev_id,
                    )
                    failed_crids.add(rev_id)
                elif rev_id in used_ids:
                    LOGGER.warn(
                        "Skipping requested credential revocation"
                        "on rev reg id %s, cred rev id=%s already revoked",
                        revoc_reg_id,
                        rev_id,
                    )
                    failed_crids.add(rev_id)
                else:
                    rev_crids.add(rev_id)

            if not rev_crids:
                break

            try:
                prev_list = RevocationStatusList.load(rev_list_entry.raw_value)
            except AnoncredsError as err:
                raise AnonCredsIssuerError("Error loading revocation registry") from err

            try:
                updated_list = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: prev_list.update(
                        int(time.time()),
                        None,  # issued
                        list(rev_crids),  # revoked
                        rev_reg_def,
                    ),
                )
            except AnoncredsError as err:
                raise AnonCredsIssuerError(
                    "Error updating revocation registry"
                ) from err

            try:
                async with self._profile.transaction() as txn:
                    rev_list_upd = await txn.handle.fetch(
                        CATEGORY_REV_LIST, revoc_reg_id, for_update=True
                    )
                    rev_info_upd = await txn.handle.fetch(
                        CATEGORY_REV_REG_INFO, revoc_reg_id, for_update=True
                    )
                    if not rev_list_upd or not rev_reg_info:
                        LOGGER.warn(
                            "Revocation registry missing, skipping update: {}",
                            revoc_reg_id,
                        )
                        updated_list = None
                        break
                    rev_info_upd = rev_info_upd.value_json
                    if rev_info_upd != rev_info:
                        # handle concurrent update to the registry by retrying
                        continue
                    await txn.handle.replace(
                        CATEGORY_REV_LIST,
                        revoc_reg_id,
                        updated_list.to_json_buffer(),
                    )
                    used_ids.update(rev_crids)
                    rev_info_upd["used_ids"] = sorted(used_ids)
                    await txn.handle.replace(
                        CATEGORY_REV_REG_INFO, revoc_reg_id, value_json=rev_info_upd
                    )
                    await txn.commit()
            except AskarError as err:
                raise AnonCredsIssuerError("Error saving revocation registry") from err
            break

        return RevokeResult(
            prev=prev_list,
            curr=updated_list,
            failed=[str(rev_id) for rev_id in sorted(failed_crids)],
        )

    async def merge_revocation_registry_deltas(
        self, fro_delta: str, to_delta: str
    ) -> str:
        """
        Merge revocation registry deltas.

        Args:
            fro_delta: original delta in JSON format
            to_delta: incoming delta in JSON format

        Returns:
            Merged delta in JSON format

        """

        def update(d1, d2):
            try:
                delta = RevocationRegistryDelta.load(d1)
                delta.update_with(d2)
                return delta.to_json()
            except AnoncredsError as err:
                raise AnonCredsIssuerError(
                    "Error merging revocation registry deltas"
                ) from err

        return await asyncio.get_event_loop().run_in_executor(
            None, update, fro_delta, to_delta
        )
