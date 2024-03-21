"""anoncreds-rs issuer implementation."""

import asyncio
import logging
from time import time
from typing import Optional, Sequence

from anoncreds import (
    AnoncredsError,
    Credential,
    CredentialDefinition,
    CredentialDefinitionPrivate,
    CredentialOffer,
    KeyCorrectnessProof,
    Schema,
)
from aries_askar import AskarError

from ..askar.profile_anon import (
    AskarAnoncredsProfile,
    AskarAnoncredsProfileSession,
)
from ..core.error import BaseError
from ..core.event_bus import Event, EventBus
from ..core.profile import Profile
from .base import (
    AnonCredsSchemaAlreadyExists,
    BaseAnonCredsError,
)
from .error_messages import ANONCREDS_PROFILE_REQUIRED_MSG
from .events import CredDefFinishedEvent
from .models.anoncreds_cred_def import CredDef, CredDefResult
from .models.anoncreds_schema import AnonCredsSchema, SchemaResult, SchemaState
from .registry import AnonCredsRegistry

LOGGER = logging.getLogger(__name__)

DEFAULT_CRED_DEF_TAG = "default"
DEFAULT_SIGNATURE_TYPE = "CL"
DEFAULT_MAX_CRED_NUM = 1000
CATEGORY_SCHEMA = "schema"
CATEGORY_CRED_DEF = "credential_def"
CATEGORY_CRED_DEF_PRIVATE = "credential_def_private"
CATEGORY_CRED_DEF_KEY_PROOF = "credential_def_key_proof"
STATE_FINISHED = "finished"

EVENT_PREFIX = "acapy::anoncreds::"
EVENT_SCHEMA = EVENT_PREFIX + CATEGORY_SCHEMA
EVENT_CRED_DEF = EVENT_PREFIX + CATEGORY_CRED_DEF
EVENT_FINISHED_SUFFIX = "::" + STATE_FINISHED


class AnonCredsIssuerError(BaseError):
    """Generic issuer error."""


class AnonCredsIssuer:
    """AnonCreds issuer class.

    This class provides methods for creating and registering AnonCreds objects
    needed to issue credentials. It also provides methods for storing and
    retrieving local representations of these objects from the wallet.

    A general pattern is followed when creating and registering objects:

    1. Create the object locally
    2. Register the object with the anoncreds registry
    3. Store the object in the wallet

    The wallet storage is used to keep track of the state of the object.

    If the object is fully registered immediately after sending to the registry
    (state of `finished`), the object is saved to the wallet with an id
    matching the id returned from the registry.

    If the object is not fully registered but pending (state of `wait`), the
    object is saved to the wallet with an id matching the job id returned from
    the registry.

    If the object fails to register (state of `failed`), the object is saved to
    the wallet with an id matching the job id returned from the registry.

    When an object finishes registration after being in a pending state (moving
    from state `wait` to state `finished`), the wallet entry matching the job id
    is removed and an entry matching the registered id is added.
    """

    def __init__(self, profile: Profile):
        """Initialize an AnonCredsIssuer instance.

        Args:
            profile: The active profile instance

        """
        self._profile = profile

    @property
    def profile(self) -> AskarAnoncredsProfile:
        """Accessor for the profile instance."""
        if not isinstance(self._profile, AskarAnoncredsProfile):
            raise ValueError(ANONCREDS_PROFILE_REQUIRED_MSG)

        return self._profile

    async def notify(self, event: Event):
        """Accessor for the event bus instance."""
        event_bus = self.profile.inject(EventBus)
        await event_bus.notify(self._profile, event)

    async def _finish_registration(
        self,
        txn: AskarAnoncredsProfileSession,
        category: str,
        job_id: str,
        registered_id: str,
    ):
        entry = await txn.handle.fetch(
            category,
            job_id,
            for_update=True,
        )
        if not entry:
            raise AnonCredsIssuerError(
                f"{category} with job id {job_id} could not be found"
            )

        tags = entry.tags
        tags["state"] = STATE_FINISHED
        await txn.handle.insert(
            category,
            registered_id,
            value=entry.value,
            tags=tags,
        )
        await txn.handle.remove(category, job_id)
        return entry

    async def store_schema(
        self,
        result: SchemaResult,
    ):
        """Store schema after reaching finished state."""
        identifier = result.job_id or result.schema_state.schema_id
        if not identifier:
            raise ValueError("Schema id or job id must be set")

        try:
            async with self.profile.session() as session:
                await session.handle.insert(
                    CATEGORY_SCHEMA,
                    identifier,
                    result.schema_state.schema.to_json(),
                    {
                        "name": result.schema_state.schema.name,
                        "version": result.schema_state.schema.version,
                        "issuer_id": result.schema_state.schema.issuer_id,
                        "state": result.schema_state.state,
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
        """Create a new credential schema and store it in the wallet.

        Args:
            issuer_id: the DID issuing the credential definition
            name: the schema name
            version: the schema version
            attr_names: a sequence of schema attribute names

        Returns:
            A SchemaResult instance

        """
        options = options or {}
        # Check if record of a similar schema already exists in our records
        async with self.profile.session() as session:
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
                    f"Schema with {name}: {version} " f"already exists for {issuer_id}",
                    schemas[0].name,
                    AnonCredsSchema.deserialize(schemas[0].value_json),
                )

        schema = Schema.create(name, version, issuer_id, attr_names)
        try:
            anoncreds_registry = self.profile.inject(AnonCredsRegistry)
            schema_result = await anoncreds_registry.register_schema(
                self.profile,
                AnonCredsSchema.from_native(schema),
                options,
            )

            await self.store_schema(schema_result)
            return schema_result

        except AnonCredsSchemaAlreadyExists as err:
            # If we find that we've previously written a schema that looks like
            # this one before but that schema is not in our wallet, add it to
            # the wallet so we can return from our get schema calls
            await self.store_schema(
                SchemaResult(
                    job_id=None,
                    schema_state=SchemaState(
                        state=SchemaState.STATE_FINISHED,
                        schema_id=err.schema_id,
                        schema=err.schema,
                    ),
                )
            )
            raise AnonCredsIssuerError(
                "Schema already exists but was not in wallet; stored in wallet"
            ) from err
        except (AnoncredsError, BaseAnonCredsError) as err:
            raise AnonCredsIssuerError("Error creating schema") from err

    async def finish_schema(self, job_id: str, schema_id: str):
        """Mark a schema as finished."""
        async with self.profile.transaction() as txn:
            await self._finish_registration(txn, CATEGORY_SCHEMA, job_id, schema_id)
            await txn.commit()

    async def get_created_schemas(
        self,
        name: Optional[str] = None,
        version: Optional[str] = None,
        issuer_id: Optional[str] = None,
    ) -> Sequence[str]:
        """Retrieve IDs of schemas previously created."""
        async with self.profile.session() as session:
            # TODO limit? scan?
            schemas = await session.handle.fetch_all(
                CATEGORY_SCHEMA,
                {
                    key: value
                    for key, value in {
                        "name": name,
                        "version": version,
                        "issuer_id": issuer_id,
                        "state": STATE_FINISHED,
                    }.items()
                    if value is not None
                },
            )
        # entry.name was stored as the schema's ID
        return [entry.name for entry in schemas]

    async def credential_definition_in_wallet(
        self, credential_definition_id: str
    ) -> bool:
        """Check whether a given credential definition ID is present in the wallet.

        Args:
            credential_definition_id: The credential definition ID to check
        """
        try:
            async with self.profile.session() as session:
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
        """Create a new credential definition and store it in the wallet.

        Args:
            issuer_id: the ID of the issuer creating the credential definition
            schema_id: the schema ID for the credential definition
            tag: the tag to use for the credential definition
            signature_type: the signature type to use for the credential definition
            options: any additional options to use when creating the credential definition

        Returns:
            CredDefResult: the result of the credential definition creation

        """
        options = options or {}
        support_revocation = options.get("support_revocation", False)
        if not isinstance(support_revocation, bool):
            raise ValueError("support_revocation must be a boolean")

        max_cred_num = options.get("max_cred_num", DEFAULT_MAX_CRED_NUM)
        if not isinstance(max_cred_num, int):
            raise ValueError("max_cred_num must be an integer")

        # Don't allow revocable cred def to be created without tails server base url
        if (
            not self.profile.settings.get("tails_server_base_url")
            and support_revocation
        ):
            raise AnonCredsIssuerError(
                "tails_server_base_url not configured. Can't create revocable credential definition."  # noqa: E501
            )

        anoncreds_registry = self.profile.inject(AnonCredsRegistry)
        schema_result = await anoncreds_registry.get_schema(self.profile, schema_id)

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

        try:
            cred_def_result = await anoncreds_registry.register_credential_definition(
                self.profile,
                schema_result,
                CredDef.from_native(cred_def),
                options,
            )

            await self.store_credential_definition(
                schema_result,
                cred_def_result,
                cred_def_private,
                key_proof,
                support_revocation,
                max_cred_num,
                options,
            )

            return cred_def_result
        except (AnoncredsError, BaseAnonCredsError) as err:
            raise AnonCredsIssuerError("Error creating credential definition") from err

    async def store_credential_definition(
        self,
        schema_result: SchemaResult,
        cred_def_result: CredDefResult,
        cred_def_private: CredentialDefinitionPrivate,
        key_proof: KeyCorrectnessProof,
        support_revocation: bool,
        max_cred_num: int,
        options: Optional[dict] = None,
    ):
        """Store the cred def and it's components in the wallet."""
        options = options or {}
        identifier = (
            cred_def_result.job_id
            or cred_def_result.credential_definition_state.credential_definition_id
        )

        if not identifier:
            raise AnonCredsIssuerError("cred def id or job id required")

        try:
            async with self.profile.transaction() as txn:
                await txn.handle.insert(
                    CATEGORY_CRED_DEF,
                    identifier,
                    cred_def_result.credential_definition_state.credential_definition.to_json(),
                    tags={
                        "schema_id": schema_result.schema_id,
                        "schema_issuer_id": schema_result.schema.issuer_id,
                        "issuer_id": cred_def_result.credential_definition_state.credential_definition.issuer_id,  # noqa: E501
                        "schema_name": schema_result.schema.name,
                        "schema_version": schema_result.schema.version,
                        "state": cred_def_result.credential_definition_state.state,
                        "epoch": str(int(time())),
                        # TODO We need to keep track of these but tags probably
                        # isn't ideal. This suggests that a full record object
                        # is necessary for non-private values
                        "support_revocation": str(support_revocation),
                        "max_cred_num": str(max_cred_num),
                    },
                )
                await txn.handle.insert(
                    CATEGORY_CRED_DEF_PRIVATE,
                    identifier,
                    cred_def_private.to_json_buffer(),
                )
                await txn.handle.insert(
                    CATEGORY_CRED_DEF_KEY_PROOF, identifier, key_proof.to_json_buffer()
                )
                await txn.commit()
            if cred_def_result.credential_definition_state.state == STATE_FINISHED:
                await self.notify(
                    CredDefFinishedEvent.with_payload(
                        schema_result.schema_id,
                        identifier,
                        cred_def_result.credential_definition_state.credential_definition.issuer_id,
                        support_revocation,
                        max_cred_num,
                        options,
                    )
                )
        except AskarError as err:
            raise AnonCredsIssuerError("Error storing credential definition") from err

    async def finish_cred_def(
        self, job_id: str, cred_def_id: str, options: Optional[dict] = None
    ):
        """Finish a cred def."""
        async with self.profile.transaction() as txn:
            entry = await self._finish_registration(
                txn, CATEGORY_CRED_DEF, job_id, cred_def_id
            )
            cred_def = CredDef.from_json(entry.value)
            support_revocation = entry.tags["support_revocation"] == "True"
            max_cred_num = int(entry.tags["max_cred_num"])

            await self._finish_registration(
                txn, CATEGORY_CRED_DEF_PRIVATE, job_id, cred_def_id
            )
            await self._finish_registration(
                txn, CATEGORY_CRED_DEF_KEY_PROOF, job_id, cred_def_id
            )
            await txn.commit()

        await self.notify(
            CredDefFinishedEvent.with_payload(
                schema_id=cred_def.schema_id,
                cred_def_id=cred_def_id,
                issuer_id=cred_def.issuer_id,
                support_revocation=support_revocation,
                max_cred_num=max_cred_num,
                options=options,
            )
        )

    async def get_created_credential_definitions(
        self,
        issuer_id: Optional[str] = None,
        schema_issuer_id: Optional[str] = None,
        schema_id: Optional[str] = None,
        schema_name: Optional[str] = None,
        schema_version: Optional[str] = None,
        epoch: Optional[str] = None,
    ) -> Sequence[str]:
        """Retrieve IDs of credential definitions previously created."""
        async with self.profile.session() as session:
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
                        "epoch": epoch,
                        "state": STATE_FINISHED,
                    }.items()
                    if value is not None
                },
            )
        # entry.name is cred def id when state == finished
        return [entry.name for entry in credential_definition_entries]

    async def match_created_credential_definitions(
        self,
        cred_def_id: Optional[str] = None,
        issuer_id: Optional[str] = None,
        schema_issuer_id: Optional[str] = None,
        schema_id: Optional[str] = None,
        schema_name: Optional[str] = None,
        schema_version: Optional[str] = None,
        epoch: Optional[str] = None,
    ) -> Optional[str]:
        """Return cred def id of most recent matching cred def."""
        async with self.profile.session() as session:
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
                            "state": STATE_FINISHED,
                            "epoch": epoch,
                        }.items()
                        if value is not None
                    },
                )
                cred_def_entry = max(
                    list(credential_definition_entries),
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

    async def create_credential_offer(self, credential_definition_id: str) -> str:
        """Create a credential offer for the given credential definition id.

        Args:
            credential_definition_id: The credential definition to create an offer for

        Returns:
            The new credential offer

        """
        try:
            async with self.profile.session() as session:
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
        credential_offer: dict,
        credential_request: dict,
        credential_values: dict,
    ) -> str:
        """Create Credential."""
        anoncreds_registry = self.profile.inject(AnonCredsRegistry)
        schema_id = credential_offer["schema_id"]
        schema_result = await anoncreds_registry.get_schema(self.profile, schema_id)
        cred_def_id = credential_offer["cred_def_id"]
        schema_attributes = schema_result.schema_value.attr_names

        try:
            async with self.profile.session() as session:
                cred_def = await session.handle.fetch(CATEGORY_CRED_DEF, cred_def_id)
                cred_def_private = await session.handle.fetch(
                    CATEGORY_CRED_DEF_PRIVATE, cred_def_id
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

        try:
            credential = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: Credential.create(
                    cred_def.raw_value,
                    cred_def_private.raw_value,
                    credential_offer,
                    credential_request,
                    raw_values,
                ),
            )
        except AnoncredsError as err:
            raise AnonCredsIssuerError("Error creating credential") from err

        return credential.to_json()
