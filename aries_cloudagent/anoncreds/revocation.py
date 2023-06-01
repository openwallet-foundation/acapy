"""Revocation through ledger agnostic AnonCreds interface."""

import asyncio
import hashlib
import http
import json
import logging
import os
from pathlib import Path
import time
from typing import List, NamedTuple, Optional, Sequence, Tuple
from urllib.parse import urlparse

from anoncreds import (
    AnoncredsError,
    Credential,
    CredentialRevocationConfig,
    RevocationRegistryDefinition,
    RevocationStatusList,
)
from aries_askar.error import AskarError
import base58
from requests import RequestException, Session


from ..askar.profile import AskarProfile, AskarProfileSession
from ..core.error import BaseError
from ..core.profile import Profile
from ..tails.base import BaseTailsServer
from .issuer import (
    AnonCredsIssuer,
    CATEGORY_CRED_DEF,
    CATEGORY_CRED_DEF_PRIVATE,
    STATE_FINISHED,
)
from .models.anoncreds_revocation import (
    RevList,
    RevRegDef,
    RevRegDefResult,
    RevRegDefState,
)
from .registry import AnonCredsRegistry
from .util import indy_client_dir

LOGGER = logging.getLogger(__name__)

CATEGORY_REV_LIST = "revocation_list"
CATEGORY_REV_REG_INFO = "revocation_reg_info"
CATEGORY_REV_REG_DEF = "revocation_reg_def"
CATEGORY_REV_REG_DEF_PRIVATE = "revocation_reg_def_private"
CATEGORY_REV_REG_ISSUER = "revocation_reg_def_issuer"
STATE_REVOCATION_POSTED = "posted"
STATE_REVOCATION_PENDING = "pending"
REV_REG_DEF_STATE_ACTIVE = "active"


class AnonCredsRevocationError(BaseError):
    """Generic revocation error."""


class AnonCredsRevocationRegistryFullError(AnonCredsRevocationError):
    """Revocation registry is full when issuing a new credential."""


class RevokeResult(NamedTuple):
    prev: Optional[RevocationStatusList] = None
    curr: Optional[RevocationStatusList] = None
    failed: Optional[Sequence[str]] = None


class AnonCredsRevocation:
    """Revocation registry operations manager."""

    def __init__(self, profile: Profile):
        """
        Initialize an AnonCredsRevocation instance.

        Args:
            profile: The active profile instance

        """
        self._profile = profile

    @property
    def profile(self) -> AskarProfile:
        """Accessor for the profile instance."""
        if not isinstance(self._profile, AskarProfile):
            raise ValueError("AnonCreds interface requires Askar")

        return self._profile

    # Revocation artifact management

    async def _finish_registration(
        self,
        txn: AskarProfileSession,
        category: str,
        job_id: str,
        registered_id: str,
        *,
        state: Optional[str] = None,
    ):
        entry = await txn.handle.fetch(
            category,
            job_id,
            for_update=True,
        )
        if not entry:
            raise AnonCredsRevocationError(
                f"{category} with job id {job_id} could not be found"
            )

        if state:
            tags = entry.tags
            tags["state"] = state
        else:
            tags = entry.tags

        await txn.handle.insert(
            category,
            registered_id,
            value=entry.value,
            tags=tags,
        )
        await txn.handle.remove(category, job_id)

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
        Create a new revocation registry and register on network.

        Args:
            issuer_id (str): issuer identifier
            cred_def_id (str): credential definition identifier
            registry_type (str): revocation registry type
            tag (str): revocation registry tag
            max_cred_num (int): maximum number of credentials supported
            options (dict): revocation registry options

        Returns:
            RevRegDefResult: revocation registry definition result

        """
        try:
            async with self.profile.session() as session:
                cred_def = await session.handle.fetch(CATEGORY_CRED_DEF, cred_def_id)
        except AskarError as err:
            raise AnonCredsRevocationError(
                "Error retrieving credential definition"
            ) from err

        if not cred_def:
            raise AnonCredsRevocationError(
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
        except AnoncredsError as err:
            raise AnonCredsRevocationError(
                "Error creating revocation registry"
            ) from err

        rev_reg_def = RevRegDef.from_native(rev_reg_def)

        public_tails_uri = self.generate_public_tails_uri(rev_reg_def)
        rev_reg_def.value.tails_location = public_tails_uri
        anoncreds_registry = self.profile.inject(AnonCredsRegistry)
        result = await anoncreds_registry.register_revocation_registry_definition(
            self.profile, rev_reg_def, options
        )

        ident = result.rev_reg_def_id or result.job_id
        if not ident:
            raise AnonCredsRevocationError(
                "Revocation registry definition id or job id not found"
            )

        # TODO Handle `failed` state

        try:
            async with self.profile.transaction() as txn:
                await txn.handle.insert(
                    CATEGORY_REV_REG_DEF,
                    ident,
                    rev_reg_def.to_json(),
                    tags={
                        "cred_def_id": cred_def_id,
                        "state": result.revocation_registry_definition_state.state,
                    },
                )
                await txn.handle.insert(
                    CATEGORY_REV_REG_INFO,
                    ident,
                    value_json={"curr_id": 0, "used_ids": []},
                )
                await txn.handle.insert(
                    CATEGORY_REV_REG_DEF_PRIVATE,
                    ident,
                    rev_reg_def_private.to_json_buffer(),
                )
                await txn.commit()
        except AskarError as err:
            raise AnonCredsRevocationError(
                "Error saving new revocation registry"
            ) from err

        return result

    async def finish_revocation_registry_definition(
        self, job_id: str, rev_reg_def_id: str
    ):
        """Mark a rev reg def as finished."""
        async with self.profile.transaction() as txn:
            await self._finish_registration(
                txn, CATEGORY_REV_REG_DEF, job_id, rev_reg_def_id, state=STATE_FINISHED
            )
            await self._finish_registration(
                txn,
                CATEGORY_REV_REG_INFO,
                job_id,
                rev_reg_def_id,
            )
            await self._finish_registration(
                txn,
                CATEGORY_REV_REG_DEF_PRIVATE,
                job_id,
                rev_reg_def_id,
            )
            await txn.commit()

    async def get_created_revocation_registry_definitions(
        self,
        cred_def_id: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Sequence[str]:
        """Retrieve IDs of rev reg defs previously created."""
        async with self.profile.session() as session:
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

    async def get_created_revocation_registry_definition(
        self,
        rev_reg_def_id: str,
    ) -> Optional[RevRegDef]:
        """Retrieve rev reg def by ID from rev reg defs previously created."""
        async with self.profile.session() as session:
            rev_reg_def_entry = await session.handle.fetch(
                CATEGORY_REV_REG_DEF,
                name=rev_reg_def_id,
            )

        if rev_reg_def_entry:
            return RevRegDef.deserialize(rev_reg_def_entry.value_json)

        return None

    async def set_active_registry(self, cred_def_id: str, rev_reg_def_id: str):
        """Mark a registry as active."""
        async with self.profile.transaction() as txn:
            entry = await txn.handle.fetch(
                CATEGORY_REV_REG_DEF,
                rev_reg_def_id,
                for_update=True,
            )
            if not entry:
                raise AnonCredsRevocationError(
                    f"{CATEGORY_REV_REG_DEF} with id "
                    f"{rev_reg_def_id} could not be found"
                )

            if entry.tags["active"] == json.dumps(True):
                # NOTE If there are other registries set as active, we're not
                # clearing them if the one we want to be active is already
                # active. This probably isn't an issue.
                return

            old_active_entries = await txn.handle.fetch_all(
                CATEGORY_REV_REG_DEF,
                {
                    "active": json.dumps(True),
                    "cred_def_id": cred_def_id,
                },
                for_update=True,
            )

            if len(old_active_entries) > 1:
                LOGGER.error(
                    "More than one registry was set as active for "
                    f"cred def {cred_def_id}; clearing active tag from all records"
                )

            for old_entry in old_active_entries:
                tags = old_entry.tags
                tags["active"] = json.dumps(False)
                await txn.handle.replace(
                    CATEGORY_REV_REG_DEF,
                    old_entry.name,
                    old_entry.value,
                    tags,
                )

            tags = entry.tags
            tags["active"] = json.dumps(True)
            await txn.handle.insert(
                CATEGORY_REV_REG_DEF,
                rev_reg_def_id,
                value=entry.value,
                tags=tags,
            )
            await txn.commit()

    async def create_and_register_revocation_list(
        self, rev_reg_def_id: str, options: Optional[dict] = None
    ):
        """Create and register a revocation list."""
        try:
            async with self.profile.session() as session:
                rev_reg_def_entry = await session.handle.fetch(
                    CATEGORY_REV_REG_DEF, rev_reg_def_id
                )
        except AskarError as err:
            raise AnonCredsRevocationError(
                "Error retrieving credential definition"
            ) from err

        if not rev_reg_def_entry:
            raise AnonCredsRevocationError(
                f"Revocation registry definition not found for id {rev_reg_def_id}"
            )

        rev_reg_def = RevRegDef.deserialize(rev_reg_def_entry.value_json)
        # TODO This is a little rough; stored tails location will have public uri
        rev_reg_def.value.tails_location = self.get_local_tails_path(rev_reg_def)

        rev_list = RevocationStatusList.create(
            rev_reg_def_id,
            rev_reg_def.to_native(),
            rev_reg_def.issuer_id,
        )

        anoncreds_registry = self.profile.inject(AnonCredsRegistry)
        result = await anoncreds_registry.register_revocation_list(
            self.profile, rev_reg_def, RevList.from_native(rev_list), options
        )

        # TODO Handle `failed` state

        posted = result.revocation_list_state.revocation_list
        try:
            async with self.profile.session() as session:
                await session.handle.insert(
                    CATEGORY_REV_LIST,
                    rev_reg_def_id,
                    value_json={
                        "posted": posted.serialize(),
                        "pending": None,
                    },
                    tags={"state": result.revocation_list_state.state},
                )
        except AskarError as err:
            raise AnonCredsRevocationError(
                "Error saving new revocation registry"
            ) from err

        return result

    async def finish_revocation_list(self, rev_reg_def_id: str):
        """Mark a revocation list as finished."""
        async with self.profile.transaction() as txn:
            entry = await txn.handle.fetch(
                CATEGORY_REV_LIST,
                rev_reg_def_id,
                for_update=True,
            )
            if not entry:
                raise AnonCredsRevocationError(
                    f"revocation list with id {rev_reg_def_id} could not be found"
                )

            await txn.handle.replace(
                CATEGORY_REV_LIST,
                rev_reg_def_id,
                value=entry.value,
                tags={"state": STATE_FINISHED},
            )
            await txn.commit()

    async def mark_pending_revocations(self, rev_reg_def_id: str, *crids: int):
        async with self.profile.transaction() as txn:
            entry = await txn.handle.fetch(
                CATEGORY_REV_REG_DEF,
                rev_reg_def_id,
            )
            if not entry:
                raise AnonCredsRevocationError(
                    "Revocation registry definition not found for id {rev_reg_def_id}"
                )
            rev_reg_def = RevocationRegistryDefinition.load(entry.value)

            entry = await txn.handle.fetch(
                CATEGORY_REV_LIST,
                rev_reg_def_id,
                for_update=True,
            )

            if not entry:
                raise AnonCredsRevocationError(
                    "Revocation list with id {rev_reg_def_id} not found"
                )

            posted = RevocationStatusList.load(entry.value_json["posted"])
            if entry.value_json["pending"]:
                pending = RevocationStatusList.load(entry.value_json["pending"])
            else:
                pending = posted

            pending = pending.update(
                timestamp=None, issued=None, revoked=crids, rev_reg_def=rev_reg_def
            )

            await txn.handle.replace(
                CATEGORY_REV_LIST,
                rev_reg_def_id,
                value_json={
                    "posted": posted.to_dict(),
                    "pending": pending.to_dict(),
                },
            )
            await txn.commit()

    async def clear_pending_revocations(self, rev_reg_def_id: str):
        async with self.profile.transaction() as txn:
            entry = await txn.handle.fetch(
                CATEGORY_REV_LIST,
                rev_reg_def_id,
                for_update=True,
            )

            if not entry:
                raise AnonCredsRevocationError(
                    "Revocation list with id {rev_reg_def_id} not found"
                )

            await txn.handle.replace(
                CATEGORY_REV_LIST,
                rev_reg_def_id,
                value_json={"posted": entry.value_json["posted"], "pending": None},
            )
            await txn.commit()

    async def retrieve_tails(self, rev_reg_def: RevRegDef) -> str:
        """Retrieve tails file from server."""
        LOGGER.info(
            "Downloading the tails file with hash: %s",
            rev_reg_def.value.tails_hash,
        )

        tails_file_path = Path(self.get_local_tails_path(rev_reg_def))
        tails_file_dir = tails_file_path.parent
        if not tails_file_dir.exists():
            tails_file_dir.mkdir(parents=True)

        buffer_size = 65536  # should be multiple of 32 bytes for sha256
        file_hasher = hashlib.sha256()
        with open(tails_file_path, "wb", buffer_size) as tails_file:
            with Session() as req_session:
                try:
                    resp = req_session.get(
                        rev_reg_def.value.tails_location, stream=True
                    )
                    # Should this directly raise an Error?
                    if resp.status_code != http.HTTPStatus.OK:
                        LOGGER.warning(
                            f"Unexpected status code for tails file: {resp.status_code}"
                        )
                    for buf in resp.iter_content(chunk_size=buffer_size):
                        tails_file.write(buf)
                        file_hasher.update(buf)
                except RequestException as rx:
                    raise AnonCredsRevocationError(f"Error retrieving tails file: {rx}")

        download_tails_hash = base58.b58encode(file_hasher.digest()).decode("utf-8")
        if download_tails_hash != rev_reg_def.value.tails_hash:
            try:
                os.remove(tails_file_path)
            except OSError as err:
                LOGGER.warning(f"Could not delete invalid tails file: {err}")

            raise AnonCredsRevocationError(
                "The hash of the downloaded tails file does not match."
            )

        return str(tails_file_path)

    def _check_url(self, url) -> None:
        parsed = urlparse(url)
        if not (parsed.scheme and parsed.netloc and parsed.path):
            raise AnonCredsRevocationError("URI {} is not a valid URL".format(url))

    def generate_public_tails_uri(self, rev_reg_def: RevRegDef):
        """Construct tails uri from rev_reg_def."""
        tails_base_url = self.profile.settings.get("tails_server_base_url")
        if not tails_base_url:
            raise AnonCredsRevocationError("tails_server_base_url not configured")

        public_tails_uri = (
            tails_base_url.rstrip("/") + f"/hash/{rev_reg_def.value.tails_hash}"
        )

        self._check_url(public_tails_uri)
        return public_tails_uri

    def get_local_tails_path(self, rev_reg_def: RevRegDef) -> str:
        """Get the local path to the tails file."""
        tails_dir = indy_client_dir("tails", create=False)
        return os.path.join(tails_dir, rev_reg_def.value.tails_hash)

    async def upload_tails_file(self, rev_reg_def: RevRegDef):
        """Upload the local tails file to the tails server."""
        tails_server = self.profile.inject_or(BaseTailsServer)
        if not tails_server:
            raise AnonCredsRevocationError("Tails server not configured")
        if not Path(self.get_local_tails_path(rev_reg_def)).is_file():
            raise AnonCredsRevocationError("Local tails file not found")

        (upload_success, result) = await tails_server.upload_tails_file(
            self.profile.context,
            rev_reg_def.value.tails_hash,
            self.get_local_tails_path(rev_reg_def),
            interval=0.8,
            backoff=-0.5,
            max_attempts=5,  # heuristic: respect HTTP timeout
        )
        if not upload_success:
            raise AnonCredsRevocationError(
                f"Tails file for rev reg for {rev_reg_def.cred_def_id} "
                f"failed to upload: {result}"
            )
        if rev_reg_def.value.tails_location != result:
            raise AnonCredsRevocationError(
                f"Tails file for rev reg for {rev_reg_def.cred_def_id} "
                f"uploaded to wrong location: {result} "
                f"(should have been {rev_reg_def.value.tails_location})"
            )

    async def get_or_fetch_local_tails_path(self, rev_reg_def: RevRegDef) -> str:
        """Return path to local tails file.

        If not present, retrieve from tails server.
        """
        tails_file_path = self.get_local_tails_path(rev_reg_def)
        if Path(tails_file_path).is_file():
            return tails_file_path
        return await self.retrieve_tails(rev_reg_def)

    # Registry Management

    async def handle_full_registry(self, rev_reg_def_id: str):
        """Update the registry status and start the next registry generation."""
        # TODO

    async def get_or_create_active_registry(self, cred_def_id: str) -> RevRegDefResult:
        """Get or create a revocation registry for the given cred def id."""
        async with self.profile.session() as session:
            rev_reg_defs = await session.handle.fetch_all(
                CATEGORY_REV_REG_DEF,
                {
                    "cred_def_id": cred_def_id,
                    "active": json.dumps(True),
                },
                limit=1,
            )

        if not rev_reg_defs:
            # TODO Create a registry if none available
            raise AnonCredsRevocationError("No active registry")

        entry = rev_reg_defs[0]

        rev_reg_def = RevRegDef.deserialize(entry.value_json)
        result = RevRegDefResult(
            None,
            RevRegDefState(
                state=STATE_FINISHED,
                revocation_registry_definition_id=entry.name,
                revocation_registry_definition=rev_reg_def,
            ),
            registration_metadata={},
            revocation_registry_definition_metadata={},
        )
        return result

    # Credential Operations

    async def _create_credential(
        self,
        credential_definition_id: str,
        schema_attributes: List[str],
        credential_offer: dict,
        credential_request: dict,
        credential_values: dict,
        rev_reg_def_id: Optional[str] = None,
        tails_file_path: Optional[str] = None,
    ) -> Tuple[str, str]:
        try:
            async with self.profile.session() as session:
                cred_def = await session.handle.fetch(
                    CATEGORY_CRED_DEF, credential_definition_id
                )
                cred_def_private = await session.handle.fetch(
                    CATEGORY_CRED_DEF_PRIVATE, credential_definition_id
                )
        except AskarError as err:
            raise AnonCredsRevocationError(
                "Error retrieving credential definition"
            ) from err
        if not cred_def or not cred_def_private:
            raise AnonCredsRevocationError(
                "Credential definition not found for credential issuance"
            )

        raw_values = {}
        for attribute in schema_attributes:
            # Ensure every attribute present in schema to be set.
            # Extraneous attribute names are ignored.
            try:
                credential_value = credential_values[attribute]
            except KeyError:
                raise AnonCredsRevocationError(
                    "Provided credential values are missing a value "
                    f"for the schema attribute '{attribute}'"
                )

            raw_values[attribute] = str(credential_value)

        if rev_reg_def_id and tails_file_path:
            try:
                async with self.profile.transaction() as txn:
                    rev_list = await txn.handle.fetch(CATEGORY_REV_LIST, rev_reg_def_id)
                    rev_reg_info = await txn.handle.fetch(
                        CATEGORY_REV_REG_INFO, rev_reg_def_id, for_update=True
                    )
                    rev_reg_def = await txn.handle.fetch(
                        CATEGORY_REV_REG_DEF, rev_reg_def_id
                    )
                    rev_key = await txn.handle.fetch(
                        CATEGORY_REV_REG_DEF_PRIVATE, rev_reg_def_id
                    )
                    if not rev_list:
                        raise AnonCredsRevocationError("Revocation registry not found")
                    if not rev_reg_info:
                        raise AnonCredsRevocationError(
                            "Revocation registry metadata not found"
                        )
                    if not rev_reg_def:
                        raise AnonCredsRevocationError(
                            "Revocation registry definition not found"
                        )
                    if not rev_key:
                        raise AnonCredsRevocationError(
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
                        raise AnonCredsRevocationError(
                            "Error loading revocation registry definition"
                        ) from err
                    if rev_reg_index > rev_reg_def.max_cred_num:
                        raise AnonCredsRevocationRegistryFullError(
                            "Revocation registry is full"
                        )
                    rev_info["curr_id"] = rev_reg_index
                    await txn.handle.replace(
                        CATEGORY_REV_REG_INFO, rev_reg_def_id, value_json=rev_info
                    )
                    await txn.commit()
            except AskarError as err:
                raise AnonCredsRevocationError(
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
                    rev_reg_def_id,
                    rev_list,
                    revoc,
                ),
            )
        except AnoncredsError as err:
            raise AnonCredsRevocationError("Error creating credential") from err

        return credential.to_json(), credential_revocation_id

    async def create_credential(
        self,
        credential_offer: dict,
        credential_request: dict,
        credential_values: dict,
        *,
        retries: int = 5,
    ) -> Tuple[str, str, str]:
        """
        Create a credential.

        Args
            credential_offer: Credential Offer to create credential for
            credential_request: Credential request to create credential for
            credential_values: Values to go in credential
            revoc_reg_id: ID of the revocation registry
            retries: number of times to retry credential creation

        Returns:
            A tuple of created credential and revocation id

        """
        issuer = AnonCredsIssuer(self.profile)
        anoncreds_registry = self.profile.inject(AnonCredsRegistry)
        schema_id = credential_offer["schema_id"]
        schema_result = await anoncreds_registry.get_schema(self.profile, schema_id)
        cred_def_id = credential_offer["cred_def_id"]

        revocable = await issuer.cred_def_supports_revocation(cred_def_id)

        for attempt in range(max(retries, 1)):
            if attempt > 0:
                LOGGER.info(
                    "Waiting 2s before retrying credential issuance for cred def '%s'",
                    cred_def_id,
                )
                await asyncio.sleep(2)

            rev_reg_def_result = None
            if revocable:
                rev_reg_def_result = await self.get_or_create_active_registry(
                    cred_def_id
                )
                if (
                    rev_reg_def_result.revocation_registry_definition_state.state
                    != STATE_FINISHED
                ):
                    continue
                rev_reg_def_id = rev_reg_def_result.rev_reg_def_id
                tails_file_path = self.get_local_tails_path(
                    rev_reg_def_result.rev_reg_def
                )
            else:
                rev_reg_def_id = None
                tails_file_path = None

            try:
                cred_json, cred_rev_id = await self._create_credential(
                    cred_def_id,
                    schema_result.schema_value.attr_names,
                    credential_offer,
                    credential_request,
                    credential_values,
                    rev_reg_def_id,
                    tails_file_path,
                )
            except AnonCredsRevocationRegistryFullError:
                # unlucky, another instance filled the registry first
                continue

            if (
                rev_reg_def_result
                and rev_reg_def_result.rev_reg_def.value.max_cred_num
                <= int(cred_rev_id)
            ):
                await self.handle_full_registry(rev_reg_def_id)

            return cred_json, cred_rev_id, rev_reg_def_id

        raise AnonCredsRevocationError(
            f"Cred def '{cred_def_id}' has no active revocation registry"
        )

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
                raise AnonCredsRevocationError(
                    "Repeated conflict attempting to update registry"
                )
            try:
                async with self.profile.session() as session:
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
                    raise AnonCredsRevocationError(
                        "Revocation registry definition not found"
                    )
                if not rev_list_entry:
                    raise AnonCredsRevocationError("Revocation registry not found")
                if not rev_reg_info:
                    raise AnonCredsRevocationError(
                        "Revocation registry metadata not found"
                    )
            except AskarError as err:
                raise AnonCredsRevocationError(
                    "Error retrieving revocation registry"
                ) from err

            try:
                rev_reg_def = RevocationRegistryDefinition.load(
                    rev_reg_def_entry.raw_value
                )
            except AnoncredsError as err:
                raise AnonCredsRevocationError(
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
                raise AnonCredsRevocationError(
                    "Error loading revocation registry"
                ) from err

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
                raise AnonCredsRevocationError(
                    "Error updating revocation registry"
                ) from err

            try:
                async with self.profile.transaction() as txn:
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
                raise AnonCredsRevocationError(
                    "Error saving revocation registry"
                ) from err
            break

        return RevokeResult(
            prev=prev_list,
            curr=updated_list,
            failed=[str(rev_id) for rev_id in sorted(failed_crids)],
        )
