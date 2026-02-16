"""Indy issuer implementation."""

import asyncio
import logging
from typing import Optional, Sequence, Tuple

from indy_credx import (
    Credential,
    CredentialDefinition,
    CredentialOffer,
    CredentialRevocationConfig,
    CredxError,
    RevocationRegistry,
    RevocationRegistryDefinition,
    RevocationRegistryDefinitionPrivate,
    RevocationRegistryDelta,
    Schema,
)

from ...core.profile import Profile, ProfileSession
from ...database_manager.db_errors import DBError
from ...utils.general import strip_did_prefix
from ..issuer import (
    DEFAULT_CRED_DEF_TAG,
    DEFAULT_SIGNATURE_TYPE,
    IndyIssuer,
    IndyIssuerError,
    IndyIssuerRevocationRegistryFullError,
)

LOGGER = logging.getLogger(__name__)

CATEGORY_CRED_DEF = "credential_def"
CATEGORY_CRED_DEF_PRIVATE = "credential_def_private"
CATEGORY_CRED_DEF_KEY_PROOF = "credential_def_key_proof"
CATEGORY_SCHEMA = "schema"
CATEGORY_REV_REG = "revocation_reg"
CATEGORY_REV_REG_INFO = "revocation_reg_info"
CATEGORY_REV_REG_DEF = "revocation_reg_def"
CATEGORY_REV_REG_DEF_PRIVATE = "revocation_reg_def_private"
CATEGORY_REV_REG_ISSUER = "revocation_reg_def_issuer"


# Deduplicated error message constants
ERR_CREATE_SCHEMA = "Error creating schema"
ERR_STORE_SCHEMA = "Error storing schema"
ERR_CHECK_CRED_DEF = "Error checking for credential definition"
ERR_CREATE_CRED_DEF = "Error creating credential definition"
ERR_STORE_CRED_DEF = "Error storing credential definition"
ERR_RETRIEVE_CRED_DEF = "Error retrieving credential definition"
ERR_CRED_DEF_NOT_FOUND_OFFER = "Credential definition not found for credential offer"
ERR_CREATE_CRED_OFFER = "Error creating credential offer"
ERR_CRED_DEF_NOT_FOUND_ISSUE = "Credential definition not found for credential issuance"
ERR_MISSING_SCHEMA_ATTR = (
    "Provided credential values are missing a value for the schema attribute '{}'"
)
ERR_UPDATE_REV_REG_INDEX = "Error updating revocation registry index"
ERR_LOAD_CRED_DEF = "Error loading credential definition"
ERR_LOAD_REV_REG_DEF = "Error loading revocation registry definition"
ERR_LOAD_REV_REG_PRIV = "Error loading revocation registry private key"
ERR_LOAD_REV_REG = "Error loading revocation registry"
ERR_UPDATE_REV_REG = "Error updating revocation registry"
ERR_SAVE_REV_REG = "Error saving revocation registry"
ERR_CREATE_CREDENTIAL = "Error creating credential"
ERR_MERGE_DELTAS = "Error merging revocation registry deltas"
ERR_RETRIEVE_CRED_DEF_FOR_REV = "Error retrieving credential definition"
ERR_CRED_DEF_NOT_FOUND_REV = "Credential definition not found for revocation registry"
ERR_CREATE_REV_REG = "Error creating revocation registry"
ERR_SAVE_NEW_REV_REG = "Error saving new revocation registry"


class KanonIndyCredxIssuer(IndyIssuer):
    """Indy-Credx issuer class."""

    def __init__(self, profile: Profile):
        """Initialize an IndyCredxIssuer instance.

        Args:
            profile: The active profile instance

        """
        self._profile = profile

    @property
    def profile(self) -> Profile:
        """Accessor for the profile instance."""
        return self._profile

    # ---------- helpers to reduce cognitive complexity ----------

    def _build_raw_values(self, schema: dict, credential_values: dict) -> dict:
        """Build raw values from schema attrNames and provided values.

        Raises IndyIssuerError if a schema attribute is missing.
        """
        raw_values: dict = {}
        schema_attributes = schema["attrNames"]
        for attribute in schema_attributes:
            try:
                credential_value = credential_values[attribute]
            except KeyError:
                raise IndyIssuerError(ERR_MISSING_SCHEMA_ATTR.format(attribute))
            raw_values[attribute] = str(credential_value)
        return raw_values

    async def _fetch_revocation_records(self, txn: ProfileSession, revoc_reg_id: str):
        """Fetch revocation records required for updates; validate presence."""
        rev_reg = await txn.handle.fetch(CATEGORY_REV_REG, revoc_reg_id)
        rev_reg_info = await txn.handle.fetch(
            CATEGORY_REV_REG_INFO, revoc_reg_id, for_update=True
        )
        rev_reg_def = await txn.handle.fetch(CATEGORY_REV_REG_DEF, revoc_reg_id)
        rev_key = await txn.handle.fetch(CATEGORY_REV_REG_DEF_PRIVATE, revoc_reg_id)
        if not rev_reg:
            raise IndyIssuerError("Revocation registry not found")
        if not rev_reg_info:
            raise IndyIssuerError("Revocation registry metadata not found")
        if not rev_reg_def:
            raise IndyIssuerError("Revocation registry definition not found")
        if not rev_key:
            raise IndyIssuerError("Revocation registry definition private data not found")
        return rev_reg, rev_reg_info, rev_reg_def, rev_key

    def _classify_revocation_ids(
        self,
        rev_info: dict,
        max_cred_num: int,
        cred_revoc_ids: Sequence[str],
        revoc_reg_id: str,
    ) -> tuple[set[int], set[int]]:
        """Classify credential revocation ids into valid and failed sets."""
        rev_crids: set[int] = set()
        failed_crids: set[int] = set()
        used_ids = set(rev_info.get("used_ids") or [])
        for rev_id in cred_revoc_ids:
            rid = int(rev_id)
            if rid < 1 or rid > max_cred_num:
                LOGGER.error(
                    "Skipping requested credential revocation"
                    "on rev reg id %s, cred rev id=%s not in range",
                    revoc_reg_id,
                    rid,
                )
                failed_crids.add(rid)
            elif rid > rev_info["curr_id"]:
                LOGGER.warning(
                    "Skipping requested credential revocation"
                    "on rev reg id %s, cred rev id=%s not yet issued",
                    revoc_reg_id,
                    rid,
                )
                failed_crids.add(rid)
            elif rid in used_ids:
                LOGGER.warning(
                    "Skipping requested credential revocation"
                    "on rev reg id %s, cred rev id=%s already revoked",
                    revoc_reg_id,
                    rid,
                )
                failed_crids.add(rid)
            else:
                rev_crids.add(rid)
        return rev_crids, failed_crids

    async def create_schema(
        self,
        origin_did: str,
        schema_name: str,
        schema_version: str,
        attribute_names: Sequence[str],
    ) -> Tuple[str, str]:
        """Create a new credential schema and store it in the wallet.

        Args:
            origin_did: the DID issuing the credential definition
            schema_name: the schema name
            schema_version: the schema version
            attribute_names: a sequence of schema attribute names

        Returns:
            A tuple of the schema ID and JSON

        """
        try:
            schema = Schema.create(
                strip_did_prefix(origin_did),
                schema_name,
                schema_version,
                attribute_names,
            )
            schema_id = schema.id
            schema_json = schema.to_json()
            async with self._profile.session() as session:
                await session.handle.insert(CATEGORY_SCHEMA, schema_id, schema_json)
        except CredxError as err:
            raise IndyIssuerError(ERR_CREATE_SCHEMA) from err
        except DBError as err:
            raise IndyIssuerError(ERR_STORE_SCHEMA) from err
        return (schema_id, schema_json)

    async def credential_definition_in_wallet(
        self, credential_definition_id: str
    ) -> bool:
        """Check whether a given credential definition ID is present in the wallet.

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
        except DBError as err:
            raise IndyIssuerError(ERR_CHECK_CRED_DEF) from err

    async def create_and_store_credential_definition(
        self,
        origin_did: str,
        schema: dict,
        signature_type: Optional[str] = None,
        tag: Optional[str] = None,
        support_revocation: bool = False,
    ) -> Tuple[str, str]:
        """Create a new credential definition and store it in the wallet.

        Args:
            origin_did (str): The DID issuing the credential definition.
            schema (dict): The schema to create a credential definition for.
            signature_type (str, optional): The credential definition signature type
                (default 'CL').
            tag (str, optional): The credential definition tag.
            support_revocation (bool, optional): Whether to enable revocation for this
                credential definition.

        Returns:
            Tuple[str, str]: A tuple of the credential definition ID and JSON.

        Raises:
            IndyIssuerError: If there is an error creating or storing the credential
                definition.

        """
        try:
            (
                cred_def,
                cred_def_private,
                key_proof,
            ) = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda origin=origin_did,
                sch=schema,
                sig=signature_type,
                tg=tag,
                sup=support_revocation: CredentialDefinition.create(
                    strip_did_prefix(origin),
                    sch,
                    sig or DEFAULT_SIGNATURE_TYPE,
                    tg or DEFAULT_CRED_DEF_TAG,
                    support_revocation=sup,
                ),
            )
            cred_def_id = cred_def.id
            cred_def_json = cred_def.to_json()
        except CredxError as err:
            raise IndyIssuerError(ERR_CREATE_CRED_DEF) from err
        try:
            async with self._profile.transaction() as txn:
                await txn.handle.insert(
                    CATEGORY_CRED_DEF,
                    cred_def_id,
                    cred_def_json,
                    # Note: Indy-SDK uses a separate SchemaId record for this
                    tags={"schema_id": schema["id"]},
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
        except DBError as err:
            raise IndyIssuerError(ERR_STORE_CRED_DEF) from err
        return (cred_def_id, cred_def_json)

    async def create_credential_offer(self, credential_definition_id: str) -> str:
        """Create a credential offer for the given credential definition id.

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
        except DBError as err:
            raise IndyIssuerError(ERR_RETRIEVE_CRED_DEF) from err
        if not cred_def or not key_proof:
            raise IndyIssuerError(ERR_CRED_DEF_NOT_FOUND_OFFER)
        try:
            # The tag holds the full name of the schema,
            # as opposed to just the sequence number
            schema_id = cred_def.tags.get("schema_id")
            cred_def = CredentialDefinition.load(cred_def.raw_value)

            credential_offer = CredentialOffer.create(
                schema_id or cred_def.schema_id,
                cred_def,
                key_proof.raw_value,
            )
        except CredxError as err:
            raise IndyIssuerError(ERR_CREATE_CRED_OFFER) from err

        return credential_offer.to_json()

    async def create_credential(
        self,
        schema: dict,
        credential_offer: dict,
        credential_request: dict,
        credential_values: dict,
        revoc_reg_id: Optional[str] = None,
        tails_file_path: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Create a credential.

        Args:
            schema: Schema to create credential for
            credential_offer: Credential Offer to create credential for
            credential_request: Credential request to create credential for
            credential_values: Values to go in credential
            revoc_reg_id: ID of the revocation registry
            tails_file_path: The location of the tails file

        Returns:
            A tuple of created credential and revocation id

        """
        credential_definition_id = credential_offer["cred_def_id"]
        try:
            async with self._profile.session() as session:
                cred_def = await session.handle.fetch(
                    CATEGORY_CRED_DEF, credential_definition_id
                )
                cred_def_private = await session.handle.fetch(
                    CATEGORY_CRED_DEF_PRIVATE, credential_definition_id
                )
        except DBError as err:
            raise IndyIssuerError(ERR_RETRIEVE_CRED_DEF) from err
        if not cred_def or not cred_def_private:
            raise IndyIssuerError(ERR_CRED_DEF_NOT_FOUND_ISSUE)

        raw_values = self._build_raw_values(schema, credential_values)

        if revoc_reg_id:
            try:
                async with self._profile.transaction() as txn:
                    (
                        rev_reg,
                        rev_reg_info,
                        rev_reg_def_rec,
                        rev_key,
                    ) = await self._fetch_revocation_records(txn, revoc_reg_id)

                    rev_info = rev_reg_info.value_json
                    rev_reg_index = rev_info["curr_id"] + 1
                    try:
                        rev_reg_def = RevocationRegistryDefinition.load(
                            rev_reg_def_rec.raw_value
                        )
                    except CredxError as err:
                        raise IndyIssuerError(ERR_LOAD_REV_REG_DEF) from err
                    if rev_reg_index > rev_reg_def.max_cred_num:
                        raise IndyIssuerRevocationRegistryFullError(
                            "Revocation registry is full"
                        )
                    rev_info["curr_id"] = rev_reg_index
                    await txn.handle.replace(
                        CATEGORY_REV_REG_INFO,
                        revoc_reg_id,
                        value_json=rev_info,
                    )
                    await txn.commit()
            except DBError as err:
                raise IndyIssuerError(ERR_UPDATE_REV_REG_INDEX) from err

            revoc = CredentialRevocationConfig(
                rev_reg_def,
                rev_key.raw_value,
                rev_reg.raw_value,
                rev_reg_index,
                rev_info.get("used_ids") or [],
            )
            credential_revocation_id = str(rev_reg_index)
        else:
            revoc = None
            credential_revocation_id = None

        # This is for compatibility with an anoncreds holder
        if not credential_request.get("prover_did"):
            credential_request["prover_did"] = credential_request["entropy"]
            del credential_request["entropy"]

        try:
            (
                credential,
                _upd_rev_reg,
                _delta,
            ) = await asyncio.get_event_loop().run_in_executor(
                None,
                Credential.create,
                cred_def.raw_value,
                cred_def_private.raw_value,
                credential_offer,
                credential_request,
                raw_values,
                None,
                revoc,
            )
        except CredxError as err:
            raise IndyIssuerError(ERR_CREATE_CREDENTIAL) from err

        return credential.to_json(), credential_revocation_id

    async def revoke_credentials(
        self,
        cred_def_id: str,
        revoc_reg_id: str,
        tails_file_path: str,
        cred_revoc_ids: Sequence[str],
    ) -> Tuple[str, Sequence[str]]:
        """Revoke a set of credentials in a revocation registry.

        Args:
            cred_def_id: ID of the credential definition
            revoc_reg_id: ID of the revocation registry
            tails_file_path: path to the local tails file
            cred_revoc_ids: sequences of credential indexes in the revocation registry

        Returns:
            Tuple with the combined revocation delta, list of cred rev ids not revoked

        """
        delta = None
        failed_crids = set()
        max_attempt = 5
        attempt = 0

        while attempt < max_attempt:
            attempt += 1
            try:
                delta, failed_crids = await self._attempt_revocation(
                    cred_def_id, revoc_reg_id, cred_revoc_ids
                )
                break  # Success, exit loop
            except IndyIssuerRetryableError:
                continue  # Retry on concurrent updates
            except Exception:
                # Re-raise non-retryable exceptions immediately
                raise
        else:
            raise IndyIssuerError("Repeated conflict attempting to update registry")

        return (
            delta and delta.to_json(),
            [str(rev_id) for rev_id in sorted(failed_crids)],
        )

    # NOTE: We intentionally do not implement abstract methods here.
    # Tests use a test-only subclass.

    async def _attempt_revocation(
        self, cred_def_id: str, revoc_reg_id: str, cred_revoc_ids: Sequence[str]
    ) -> Tuple:
        """Attempt a single revocation operation."""
        # Load revocation registry components
        components = await self._load_revocation_components(cred_def_id, revoc_reg_id)

        # Classify credential revocation IDs
        rev_info = components["rev_reg_info"].value_json
        rev_crids, failed_crids = self._classify_revocation_ids(
            rev_info, components["rev_reg_def"].max_cred_num, cred_revoc_ids, revoc_reg_id
        )

        if not rev_crids:
            return None, failed_crids

        # Update revocation registry
        delta = await self._update_revocation_registry(components, list(rev_crids))

        # Save updates to storage
        await self._save_revocation_updates(
            revoc_reg_id, components["rev_reg"], rev_info, rev_crids
        )

        return delta, failed_crids

    async def _load_revocation_components(
        self, cred_def_id: str, revoc_reg_id: str
    ) -> dict:
        """Load all revocation registry components from storage."""
        try:
            async with self._profile.session() as session:
                components_raw = await self._fetch_raw_components(
                    session, cred_def_id, revoc_reg_id
                )
        except DBError as err:
            raise IndyIssuerError("Error retrieving revocation registry") from err

        return self._parse_revocation_components(components_raw)

    async def _fetch_raw_components(
        self, session: ProfileSession, cred_def_id: str, revoc_reg_id: str
    ) -> dict:
        """Fetch raw components from storage."""
        components = {
            "cred_def": await session.handle.fetch(CATEGORY_CRED_DEF, cred_def_id),
            "rev_reg_def": await session.handle.fetch(CATEGORY_REV_REG_DEF, revoc_reg_id),
            "rev_reg_def_private": await session.handle.fetch(
                CATEGORY_REV_REG_DEF_PRIVATE, revoc_reg_id
            ),
            "rev_reg": await session.handle.fetch(CATEGORY_REV_REG, revoc_reg_id),
            "rev_reg_info": await session.handle.fetch(
                CATEGORY_REV_REG_INFO, revoc_reg_id
            ),
        }

        self._validate_components_exist(components)
        return components

    def _validate_components_exist(self, components: dict):
        """Validate that all required components exist."""
        error_messages = {
            "cred_def": "Credential definition not found",
            "rev_reg_def": "Revocation registry definition not found",
            "rev_reg_def_private": "Revocation registry definition private key not found",
            "rev_reg": "Revocation registry not found",
            "rev_reg_info": "Revocation registry metadata not found",
        }

        for key, component in components.items():
            if not component:
                raise IndyIssuerError(error_messages[key])

    def _parse_revocation_components(self, components_raw: dict) -> dict:
        """Parse raw components into proper objects."""
        try:
            return {
                "cred_def": CredentialDefinition.load(
                    components_raw["cred_def"].raw_value
                ),
                "rev_reg_def": RevocationRegistryDefinition.load(
                    components_raw["rev_reg_def"].raw_value
                ),
                "rev_reg_def_private": RevocationRegistryDefinitionPrivate.load(
                    components_raw["rev_reg_def_private"].raw_value
                ),
                "rev_reg": RevocationRegistry.load(components_raw["rev_reg"].raw_value),
                "rev_reg_info": components_raw["rev_reg_info"],
            }
        except CredxError as err:
            raise IndyIssuerError("Error loading revocation registry components") from err

    async def _update_revocation_registry(self, components: dict, rev_crids: list):
        """Update the revocation registry with revoked credentials."""
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: components["rev_reg"].update(
                    components["cred_def"],
                    components["rev_reg_def"],
                    components["rev_reg_def_private"],
                    issued=None,
                    revoked=rev_crids,
                ),
            )
        except CredxError as err:
            raise IndyIssuerError(ERR_UPDATE_REV_REG) from err

    async def _save_revocation_updates(
        self, revoc_reg_id: str, rev_reg, original_rev_info: dict, rev_crids: set
    ):
        """Save revocation updates to storage."""
        try:
            async with self._profile.transaction() as txn:
                # Fetch current state for concurrent update detection
                rev_reg_upd = await txn.handle.fetch(
                    CATEGORY_REV_REG, revoc_reg_id, for_update=True
                )
                rev_info_upd = await txn.handle.fetch(
                    CATEGORY_REV_REG_INFO, revoc_reg_id, for_update=True
                )

                if not rev_reg_upd or not rev_info_upd:
                    LOGGER.warning(
                        "Revocation registry missing, skipping update: %s", revoc_reg_id
                    )
                    return

                current_rev_info = rev_info_upd.value_json
                if current_rev_info != original_rev_info:
                    # Concurrent update detected, need to retry
                    raise IndyIssuerRetryableError("Concurrent update detected")

                # Update registry and metadata
                await txn.handle.replace(
                    CATEGORY_REV_REG, revoc_reg_id, rev_reg.to_json_buffer()
                )

                used_ids = set(current_rev_info.get("used_ids") or [])
                used_ids.update(rev_crids)
                current_rev_info["used_ids"] = sorted(used_ids)

                await txn.handle.replace(
                    CATEGORY_REV_REG_INFO, revoc_reg_id, value_json=current_rev_info
                )
                await txn.commit()
        except DBError as err:
            raise IndyIssuerError(ERR_SAVE_REV_REG) from err

    async def merge_revocation_registry_deltas(
        self, fro_delta: str, to_delta: str
    ) -> str:
        """Merge revocation registry deltas.

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
            except CredxError as err:
                raise IndyIssuerError(ERR_MERGE_DELTAS) from err

        return await asyncio.get_event_loop().run_in_executor(
            None, update, fro_delta, to_delta
        )

    async def create_and_store_revocation_registry(
        self,
        origin_did: str,
        cred_def_id: str,
        revoc_def_type: str,
        tag: str,
        max_cred_num: int,
        tails_base_path: str,
    ) -> Tuple[str, str, str]:
        """Create a new revocation registry and store it in the wallet.

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
        except DBError as err:
            raise IndyIssuerError(ERR_RETRIEVE_CRED_DEF) from err
        if not cred_def:
            raise IndyIssuerError(
                "Credential definition not found for revocation registry"
            )

        try:
            (
                rev_reg_def,
                rev_reg_def_private,
                rev_reg,
                _rev_reg_delta,
            ) = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda o=origin_did,
                cd=cred_def.raw_value,
                tg=tag,
                rdt=revoc_def_type,
                mx=max_cred_num,
                td=tails_base_path: RevocationRegistryDefinition.create(
                    strip_did_prefix(o),
                    cd,
                    tg,
                    rdt,
                    mx,
                    tails_dir_path=td,
                ),
            )
        except CredxError as err:
            raise IndyIssuerError(ERR_CREATE_REV_REG) from err

        rev_reg_def_id = rev_reg_def.id
        rev_reg_def_json = rev_reg_def.to_json()
        rev_reg_json = rev_reg.to_json()

        try:
            async with self._profile.transaction() as txn:
                await txn.handle.insert(CATEGORY_REV_REG, rev_reg_def_id, rev_reg_json)
                await txn.handle.insert(
                    CATEGORY_REV_REG_INFO,
                    rev_reg_def_id,
                    value_json={"curr_id": 0, "used_ids": []},
                )
                await txn.handle.insert(
                    CATEGORY_REV_REG_DEF, rev_reg_def_id, rev_reg_def_json
                )
                await txn.handle.insert(
                    CATEGORY_REV_REG_DEF_PRIVATE,
                    rev_reg_def_id,
                    rev_reg_def_private.to_json_buffer(),
                )
                await txn.commit()
        except DBError as err:
            raise IndyIssuerError(ERR_SAVE_NEW_REV_REG) from err

        return (
            rev_reg_def_id,
            rev_reg_def_json,
            rev_reg_json,
        )


class IndyIssuerRetryableError(IndyIssuerError):
    """Error that indicates the operation should be retried."""
