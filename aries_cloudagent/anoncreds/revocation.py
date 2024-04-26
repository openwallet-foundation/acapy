"""Revocation through ledger agnostic AnonCreds interface."""

import asyncio
import hashlib
import http
import json
import logging
import os
import time
from pathlib import Path
from typing import List, NamedTuple, Optional, Sequence, Tuple
from urllib.parse import urlparse
from uuid import uuid4

import base58
from anoncreds import (
    AnoncredsError,
    Credential,
    CredentialRevocationConfig,
    RevocationRegistryDefinition,
    RevocationRegistryDefinitionPrivate,
    RevocationStatusList,
)
from aries_askar.error import AskarError
from requests import RequestException, Session

from aries_cloudagent.anoncreds.models.anoncreds_cred_def import CredDef

from ..askar.profile_anon import (
    AskarAnoncredsProfile,
    AskarAnoncredsProfileSession,
)
from ..core.error import BaseError
from ..core.event_bus import Event, EventBus
from ..core.profile import Profile, ProfileSession
from ..tails.base import BaseTailsServer
from .error_messages import ANONCREDS_PROFILE_REQUIRED_MSG
from .events import RevListFinishedEvent, RevRegDefFinishedEvent
from .issuer import (
    CATEGORY_CRED_DEF,
    CATEGORY_CRED_DEF_PRIVATE,
    STATE_FINISHED,
    AnonCredsIssuer,
)
from .models.anoncreds_revocation import (
    RevList,
    RevListResult,
    RevRegDef,
    RevRegDefResult,
    RevRegDefState,
)
from .registry import AnonCredsRegistry
from .util import indy_client_dir

LOGGER = logging.getLogger(__name__)

CATEGORY_REV_LIST = "revocation_list"
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
    """RevokeResult."""

    prev: RevList
    curr: Optional[RevList] = None
    revoked: Optional[Sequence[int]] = None
    failed: Optional[Sequence[str]] = None


class AnonCredsRevocation:
    """Revocation registry operations manager."""

    def __init__(self, profile: Profile):
        """Initialize an AnonCredsRevocation instance.

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
        """Emit an event on the event bus."""
        event_bus = self.profile.inject(EventBus)
        await event_bus.notify(self.profile, event)

    async def _finish_registration(
        self,
        txn: AskarAnoncredsProfileSession,
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
        return entry

    async def create_and_register_revocation_registry_definition(
        self,
        issuer_id: str,
        cred_def_id: str,
        registry_type: str,
        tag: str,
        max_cred_num: int,
        options: Optional[dict] = None,
    ) -> RevRegDefResult:
        """Create a new revocation registry and register on network.

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
        options = options or {}
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

        await self.store_revocation_registry_definition(
            result, rev_reg_def_private, options
        )
        return result

    async def store_revocation_registry_definition(
        self,
        result: RevRegDefResult,
        rev_reg_def_private: RevocationRegistryDefinitionPrivate,
        options: Optional[dict] = None,
    ):
        """Store a revocation registry definition."""
        options = options or {}
        identifier = result.job_id or result.rev_reg_def_id
        if not identifier:
            raise AnonCredsRevocationError(
                "Revocation registry definition id or job id not found"
            )

        # TODO Handle `failed` state

        rev_reg_def = (
            result.revocation_registry_definition_state.revocation_registry_definition
        )

        try:
            async with self.profile.transaction() as txn:
                await txn.handle.insert(
                    CATEGORY_REV_REG_DEF,
                    identifier,
                    rev_reg_def.to_json(),
                    tags={
                        "cred_def_id": rev_reg_def.cred_def_id,
                        "state": result.revocation_registry_definition_state.state,
                        "active": json.dumps(False),
                    },
                )
                await txn.handle.insert(
                    CATEGORY_REV_REG_DEF_PRIVATE,
                    identifier,
                    rev_reg_def_private.to_json_buffer(),
                )
                await txn.commit()

            if result.revocation_registry_definition_state.state == STATE_FINISHED:
                await self.notify(
                    RevRegDefFinishedEvent.with_payload(
                        identifier, rev_reg_def, options
                    )
                )
        except AskarError as err:
            raise AnonCredsRevocationError(
                "Error saving new revocation registry"
            ) from err

    async def finish_revocation_registry_definition(
        self, job_id: str, rev_reg_def_id: str, options: Optional[dict] = None
    ):
        """Mark a rev reg def as finished."""
        options = options or {}
        async with self.profile.transaction() as txn:
            entry = await self._finish_registration(
                txn, CATEGORY_REV_REG_DEF, job_id, rev_reg_def_id, state=STATE_FINISHED
            )
            rev_reg_def = RevRegDef.from_json(entry.value)
            await self._finish_registration(
                txn,
                CATEGORY_REV_REG_DEF_PRIVATE,
                job_id,
                rev_reg_def_id,
            )
            await txn.commit()

        await self.notify(
            RevRegDefFinishedEvent.with_payload(rev_reg_def_id, rev_reg_def, options)
        )

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

    async def get_created_revocation_registry_definition_state(
        self,
        rev_reg_def_id: str,
    ) -> Optional[str]:
        """Retrieve rev reg def by ID from rev reg defs previously created."""
        async with self.profile.session() as session:
            rev_reg_def_entry = await session.handle.fetch(
                CATEGORY_REV_REG_DEF,
                name=rev_reg_def_id,
            )

        if rev_reg_def_entry:
            return rev_reg_def_entry.tags.get("state")

        return None

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

    async def set_active_registry(self, rev_reg_def_id: str):
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

            cred_def_id = entry.tags["cred_def_id"]

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
            await txn.handle.replace(
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
        options = options or {}
        try:
            async with self.profile.session() as session:
                rev_reg_def_entry = await session.handle.fetch(
                    CATEGORY_REV_REG_DEF, rev_reg_def_id
                )
                rev_reg_def_private_entry = await session.handle.fetch(
                    CATEGORY_REV_REG_DEF_PRIVATE, rev_reg_def_id
                )
        except AskarError as err:
            raise AnonCredsRevocationError(
                "Error retrieving required revocation registry definition data"
            ) from err

        if not rev_reg_def_entry or not rev_reg_def_private_entry:
            raise AnonCredsRevocationError(
                (
                    "Missing required revocation registry data: "
                    "revocation registry definition"
                    if not rev_reg_def_entry
                    else ""
                ),
                (
                    "revocation registry private definition"
                    if not rev_reg_def_private_entry
                    else ""
                ),
            )

        try:
            async with self.profile.session() as session:
                cred_def_entry = await session.handle.fetch(
                    CATEGORY_CRED_DEF, rev_reg_def_entry.value_json["credDefId"]
                )
        except AskarError as err:
            raise AnonCredsRevocationError(
                f"Error retrieving cred def {rev_reg_def_entry.value_json['credDefId']}"
            ) from err

        rev_reg_def = RevRegDef.deserialize(rev_reg_def_entry.value_json)
        cred_def = CredDef.deserialize(cred_def_entry.value_json)
        rev_reg_def_private = RevocationRegistryDefinitionPrivate.load(
            rev_reg_def_private_entry.value_json
        )
        # TODO This is a little rough; stored tails location will have public uri
        rev_reg_def.value.tails_location = self.get_local_tails_path(rev_reg_def)

        rev_list = RevocationStatusList.create(
            cred_def.to_native(),
            rev_reg_def_id,
            rev_reg_def.to_native(),
            rev_reg_def_private,
            rev_reg_def.issuer_id,
        )

        anoncreds_registry = self.profile.inject(AnonCredsRegistry)
        result = await anoncreds_registry.register_revocation_list(
            self.profile, rev_reg_def, RevList.from_native(rev_list), options
        )

        # TODO Handle `failed` state
        await self.store_revocation_registry_list(result)

        return result

    async def store_revocation_registry_list(self, result: RevListResult):
        """Store a revocation registry list."""

        identifier = result.job_id or result.rev_reg_def_id
        if not identifier:
            raise AnonCredsRevocationError(
                "Revocation registry definition id or job id not found"
            )

        rev_list = result.revocation_list_state.revocation_list
        try:
            async with self.profile.session() as session:
                await session.handle.insert(
                    CATEGORY_REV_LIST,
                    identifier,
                    value_json={
                        "rev_list": rev_list.serialize(),
                        "pending": None,
                        # TODO THIS IS A HACK; this fixes ACA-Py expecting 1-based indexes  # noqa: E501
                        "next_index": 1,
                    },
                    tags={
                        "state": result.revocation_list_state.state,
                        "pending": json.dumps(False),
                    },
                )

            if result.revocation_list_state.state == STATE_FINISHED:
                await self.notify(
                    RevListFinishedEvent.with_payload(
                        rev_list.rev_reg_def_id, rev_list.revocation_list
                    )
                )

        except AskarError as err:
            raise AnonCredsRevocationError(
                "Error saving new revocation registry"
            ) from err

    async def finish_revocation_list(
        self, job_id: str, rev_reg_def_id: str, revoked: list
    ):
        """Mark a revocation list as finished."""
        async with self.profile.transaction() as txn:
            # Finish the registration if the list is new, otherwise already updated
            existing_list = await txn.handle.fetch(
                CATEGORY_REV_LIST,
                rev_reg_def_id,
            )
            if not existing_list:
                await self._finish_registration(
                    txn,
                    CATEGORY_REV_LIST,
                    job_id,
                    rev_reg_def_id,
                    state=STATE_FINISHED,
                )
                await txn.commit()
            # Notify about revoked creds on any list update
            await self.notify(
                RevListFinishedEvent.with_payload(rev_reg_def_id, revoked)
            )

    async def update_revocation_list(
        self,
        rev_reg_def_id: str,
        prev: RevList,
        curr: RevList,
        revoked: Sequence[int],
        options: Optional[dict] = None,
    ):
        """Publish and update to a revocation list."""
        options = options or {}
        try:
            async with self.profile.session() as session:
                rev_reg_def_entry = await session.handle.fetch(
                    CATEGORY_REV_REG_DEF, rev_reg_def_id
                )
        except AskarError as err:
            raise AnonCredsRevocationError(
                "Error retrieving revocation registry definition"
            ) from err

        if not rev_reg_def_entry:
            raise AnonCredsRevocationError(
                f"Revocation registry definition not found for id {rev_reg_def_id}"
            )

        try:
            async with self.profile.session() as session:
                rev_list_entry = await session.handle.fetch(
                    CATEGORY_REV_LIST, rev_reg_def_id
                )
        except AskarError as err:
            raise AnonCredsRevocationError("Error retrieving revocation list") from err

        if not rev_list_entry:
            raise AnonCredsRevocationError(
                f"Revocation list not found for id {rev_reg_def_id}"
            )

        rev_reg_def = RevRegDef.deserialize(rev_reg_def_entry.value_json)
        rev_list = RevList.deserialize(rev_list_entry.value_json["rev_list"])
        if rev_list.revocation_list != curr.revocation_list:
            raise AnonCredsRevocationError(
                "Passed revocation list does not match stored"
            )

        anoncreds_registry = self.profile.inject(AnonCredsRegistry)
        result = await anoncreds_registry.update_revocation_list(
            self.profile, rev_reg_def, prev, curr, revoked, options
        )

        # # TODO Handle `failed` state
        try:
            async with self.profile.session() as session:
                rev_list_entry_upd = await session.handle.fetch(
                    CATEGORY_REV_LIST, result.rev_reg_def_id, for_update=True
                )
                if not rev_list_entry_upd:
                    raise AnonCredsRevocationError(
                        f"Revocation list not found for id {rev_reg_def_id}"
                    )
                tags = rev_list_entry_upd.tags
                tags["state"] = result.revocation_list_state.state
                await session.handle.replace(
                    CATEGORY_REV_LIST,
                    result.rev_reg_def_id,
                    value=rev_list_entry_upd.value,
                    tags=tags,
                )
        except AskarError as err:
            raise AnonCredsRevocationError(
                "Error saving new revocation registry"
            ) from err

        return result

    async def get_created_revocation_list(
        self, rev_reg_def_id: str
    ) -> Optional[RevList]:
        """Return rev list from record in wallet."""
        try:
            async with self.profile.session() as session:
                rev_list_entry = await session.handle.fetch(
                    CATEGORY_REV_LIST, rev_reg_def_id
                )
        except AskarError as err:
            raise AnonCredsRevocationError("Error retrieving revocation list") from err

        if rev_list_entry:
            return RevList.deserialize(rev_list_entry.value_json["rev_list"])

        return None

    async def get_revocation_lists_with_pending_revocations(self) -> Sequence[str]:
        """Return a list of rev reg def ids with pending revocations."""
        try:
            async with self.profile.session() as session:
                rev_list_entries = await session.handle.fetch_all(
                    CATEGORY_REV_LIST,
                    {"pending": json.dumps(True)},
                )
        except AskarError as err:
            raise AnonCredsRevocationError("Error retrieving revocation list") from err

        if rev_list_entries:
            return [entry.name for entry in rev_list_entries]

        return []

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
        async with self.profile.session() as session:
            active_rev_reg_def = await session.handle.fetch(
                CATEGORY_REV_REG_DEF, rev_reg_def_id
            )
            if active_rev_reg_def:
                # ok, we have an active rev reg.
                # find the backup/fallover rev reg (finished and not active)
                rev_reg_defs = await session.handle.fetch_all(
                    CATEGORY_REV_REG_DEF,
                    {
                        "active": json.dumps(False),
                        "cred_def_id": active_rev_reg_def.value_json["credDefId"],
                        "state": RevRegDefState.STATE_FINISHED,
                    },
                    limit=1,
                )
                if len(rev_reg_defs):
                    backup_rev_reg_def_id = rev_reg_defs[0].name
                else:
                    # attempted to create and register here but fails in practical usage.
                    # the indexes and list do not get set properly (timing issue?)
                    # if max cred num = 4 for instance, will get
                    # Revocation status list does not have the index 4
                    # in _create_credential calling Credential.create
                    raise AnonCredsRevocationError(
                        "Error handling full registry. No backup registry available."
                    )

        # set the backup to active...
        if backup_rev_reg_def_id:
            await self.set_active_registry(backup_rev_reg_def_id)

            async with self.profile.transaction() as txn:
                # re-fetch the old active (it's been updated), we need to mark as full
                active_rev_reg_def = await txn.handle.fetch(
                    CATEGORY_REV_REG_DEF, rev_reg_def_id, for_update=True
                )
                tags = active_rev_reg_def.tags
                tags["state"] = RevRegDefState.STATE_FULL
                await txn.handle.replace(
                    CATEGORY_REV_REG_DEF,
                    active_rev_reg_def.name,
                    active_rev_reg_def.value,
                    tags,
                )
                await txn.commit()

            # create our next fallover/backup
            backup_reg = await self.create_and_register_revocation_registry_definition(
                issuer_id=active_rev_reg_def.value_json["issuerId"],
                cred_def_id=active_rev_reg_def.value_json["credDefId"],
                registry_type=active_rev_reg_def.value_json["revocDefType"],
                tag=str(uuid4()),
                max_cred_num=active_rev_reg_def.value_json["value"]["maxCredNum"],
            )
            LOGGER.info(f"previous rev_reg_def_id = {rev_reg_def_id}")
            LOGGER.info(f"current rev_reg_def_id = {backup_rev_reg_def_id}")
            LOGGER.info(f"backup reg = {backup_reg}")

    async def decommission_registry(self, cred_def_id: str):
        """Decommission post-init registries and start the next registry generation."""
        active_reg = await self.get_or_create_active_registry(cred_def_id)

        # create new one and set active
        new_reg = await self.create_and_register_revocation_registry_definition(
            issuer_id=active_reg.rev_reg_def.issuer_id,
            cred_def_id=active_reg.rev_reg_def.cred_def_id,
            registry_type=active_reg.rev_reg_def.type,
            tag=str(uuid4()),
            max_cred_num=active_reg.rev_reg_def.value.max_cred_num,
        )
        # set new as active...
        await self.set_active_registry(new_reg.rev_reg_def_id)

        # decommission everything except init/wait
        async with self.profile.transaction() as txn:
            registries = await txn.handle.fetch_all(
                CATEGORY_REV_REG_DEF,
                {
                    "cred_def_id": cred_def_id,
                },
                for_update=True,
            )

            recs = list(
                filter(
                    lambda r: r.tags.get("state") != RevRegDefState.STATE_WAIT,
                    registries,
                )
            )
            for rec in recs:
                if rec.name != new_reg.rev_reg_def_id:
                    tags = rec.tags
                    tags["active"] = json.dumps(False)
                    tags["state"] = RevRegDefState.STATE_DECOMMISSIONED
                    await txn.handle.replace(
                        CATEGORY_REV_REG_DEF,
                        rec.name,
                        rec.value,
                        tags,
                    )
            await txn.commit()
        # create a second one for backup, don't make it active
        backup_reg = await self.create_and_register_revocation_registry_definition(
            issuer_id=active_reg.rev_reg_def.issuer_id,
            cred_def_id=active_reg.rev_reg_def.cred_def_id,
            registry_type=active_reg.rev_reg_def.type,
            tag=str(uuid4()),
            max_cred_num=active_reg.rev_reg_def.value.max_cred_num,
        )

        LOGGER.info(f"new reg = {new_reg}")
        LOGGER.info(f"backup reg = {backup_reg}")
        LOGGER.info(f"decommissioned regs = {recs}")
        return recs

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
                    rev_reg_def = await txn.handle.fetch(
                        CATEGORY_REV_REG_DEF, rev_reg_def_id
                    )
                    rev_key = await txn.handle.fetch(
                        CATEGORY_REV_REG_DEF_PRIVATE, rev_reg_def_id
                    )
                    if not rev_list:
                        raise AnonCredsRevocationError("Revocation registry not found")
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
                    rev_info = rev_list.value_json
                    rev_info_tags = rev_list.tags
                    rev_reg_index = rev_info["next_index"]
                    try:
                        rev_reg_def = RevocationRegistryDefinition.load(
                            rev_reg_def.raw_value
                        )
                        rev_list = RevocationStatusList.load(rev_info["rev_list"])
                    except AnoncredsError as err:
                        raise AnonCredsRevocationError(
                            "Error loading revocation registry definition"
                        ) from err
                    if rev_reg_index > rev_reg_def.max_cred_num:
                        raise AnonCredsRevocationRegistryFullError(
                            "Revocation registry is full"
                        )
                    rev_info["next_index"] = rev_reg_index + 1
                    await txn.handle.replace(
                        CATEGORY_REV_LIST,
                        rev_reg_def_id,
                        value_json=rev_info,
                        tags=rev_info_tags,
                    )
                    await txn.commit()
            except AskarError as err:
                raise AnonCredsRevocationError(
                    "Error updating revocation registry index"
                ) from err

            # rev_info["next_index"] is 1 based but getting from
            # rev_list is zero based...
            revoc = CredentialRevocationConfig(
                rev_reg_def,
                rev_key.raw_value,
                rev_list,
                rev_reg_index,
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
        """Create a credential.

        Args:
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

            # cred rev id is zero based
            # max cred num is one based
            # however, if we wait until max cred num is reached, we are too late.
            if rev_reg_def_result:
                if (
                    rev_reg_def_result.rev_reg_def.value.max_cred_num
                    <= int(cred_rev_id) + 1
                ):
                    await self.handle_full_registry(rev_reg_def_id)

            return cred_json, cred_rev_id, rev_reg_def_id

        raise AnonCredsRevocationError(
            f"Cred def '{cred_def_id}' has no active revocation registry"
        )

    async def revoke_pending_credentials(
        self,
        revoc_reg_id: str,
        *,
        additional_crids: Optional[Sequence[int]] = None,
        limit_crids: Optional[Sequence[int]] = None,
    ) -> RevokeResult:
        """Revoke a set of credentials in a revocation registry.

        Args:
            revoc_reg_id: ID of the revocation registry
            additional_crids: sequences of additional credential indexes to revoke
            limit_crids: a sequence of credential indexes to limit revocation to
                If None, all pending revocations will be published.
                If given, the intersection of pending and limit crids will be published.

        Returns:
            Tuple with the update revocation list, list of cred rev ids not revoked

        """
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
                    rev_reg_def_private_entry = await session.handle.fetch(
                        CATEGORY_REV_REG_DEF_PRIVATE, revoc_reg_id
                    )
            except AskarError as err:
                raise AnonCredsRevocationError(
                    "Error retrieving revocation registry"
                ) from err

            if (
                not rev_reg_def_entry
                or not rev_list_entry
                or not rev_reg_def_private_entry
            ):
                raise AnonCredsRevocationError(
                    (
                        "Missing required revocation registry data: "
                        "revocation registry definition"
                        if not rev_reg_def_entry
                        else ""
                    ),
                    "revocation list" if not rev_list_entry else "",
                    (
                        "revocation registry private definition"
                        if not rev_reg_def_private_entry
                        else ""
                    ),
                )

            try:
                async with self.profile.session() as session:
                    cred_def_entry = await session.handle.fetch(
                        CATEGORY_CRED_DEF, rev_reg_def_entry.value_json["credDefId"]
                    )
            except AskarError as err:
                raise AnonCredsRevocationError(
                    f"Error retrieving cred def {rev_reg_def_entry.value_json['credDefId']}"  # noqa: E501
                ) from err

            try:
                # TODO This is a little rough; stored tails location will have public uri
                # but library needs local tails location
                rev_reg_def = RevRegDef.deserialize(rev_reg_def_entry.value_json)
                rev_reg_def.value.tails_location = self.get_local_tails_path(
                    rev_reg_def
                )
                cred_def = CredDef.deserialize(cred_def_entry.value_json)
                rev_reg_def_private = RevocationRegistryDefinitionPrivate.load(
                    rev_reg_def_private_entry.value_json
                )
            except AnoncredsError as err:
                raise AnonCredsRevocationError(
                    "Error loading revocation registry definition"
                ) from err

            rev_crids = set()
            failed_crids = set()
            max_cred_num = rev_reg_def.value.max_cred_num
            rev_info = rev_list_entry.value_json
            cred_revoc_ids = (rev_info["pending"] or []) + (additional_crids or [])
            rev_list = RevList.deserialize(rev_info["rev_list"])

            for rev_id in cred_revoc_ids:
                if rev_id < 1 or rev_id > max_cred_num:
                    LOGGER.error(
                        "Skipping requested credential revocation"
                        "on rev reg id %s, cred rev id=%s not in range",
                        revoc_reg_id,
                        rev_id,
                    )
                    failed_crids.add(rev_id)
                elif rev_id >= rev_info["next_index"]:
                    LOGGER.warning(
                        "Skipping requested credential revocation"
                        "on rev reg id %s, cred rev id=%s not yet issued",
                        revoc_reg_id,
                        rev_id,
                    )
                    failed_crids.add(rev_id)
                elif rev_list.revocation_list[rev_id] == 1:
                    LOGGER.warning(
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

            if limit_crids is None:
                skipped_crids = set()
            else:
                skipped_crids = rev_crids - set(limit_crids)
            rev_crids = rev_crids - skipped_crids

            try:
                updated_list = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: rev_list.to_native().update(
                        cred_def=cred_def.to_native(),
                        rev_reg_def=rev_reg_def.to_native(),
                        rev_reg_def_private=rev_reg_def_private,
                        issued=None,
                        revoked=list(rev_crids),
                        timestamp=int(time.time()),
                    ),
                )
            except AnoncredsError as err:
                raise AnonCredsRevocationError(
                    "Error updating revocation registry"
                ) from err

            try:
                async with self.profile.transaction() as txn:
                    rev_info_upd = await txn.handle.fetch(
                        CATEGORY_REV_LIST, revoc_reg_id, for_update=True
                    )
                    if not rev_info_upd:
                        LOGGER.warning(
                            "Revocation registry missing, skipping update: {}",
                            revoc_reg_id,
                        )
                        updated_list = None
                        break
                    tags = rev_info_upd.tags
                    rev_info_upd = rev_info_upd.value_json
                    if rev_info_upd != rev_info:
                        # handle concurrent update to the registry by retrying
                        continue
                    rev_info_upd["rev_list"] = updated_list.to_dict()
                    rev_info_upd["pending"] = (
                        list(skipped_crids) if skipped_crids else None
                    )
                    tags["pending"] = json.dumps(True if skipped_crids else False)
                    await txn.handle.replace(
                        CATEGORY_REV_LIST,
                        revoc_reg_id,
                        value_json=rev_info_upd,
                        tags=tags,
                    )
                    await txn.commit()
            except AskarError as err:
                raise AnonCredsRevocationError(
                    "Error saving revocation registry"
                ) from err
            break

        return RevokeResult(
            prev=rev_list,
            curr=RevList.from_native(updated_list) if updated_list else None,
            revoked=list(rev_crids),
            failed=[str(rev_id) for rev_id in sorted(failed_crids)],
        )

    async def mark_pending_revocations(self, rev_reg_def_id: str, *crids: int):
        """Cred rev ids stored to publish later."""
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

            pending: Optional[List[int]] = entry.value_json["pending"]
            if pending:
                pending.extend(crids)
            else:
                pending = list(crids)

            value = entry.value_json
            value["pending"] = pending
            tags = entry.tags
            tags["pending"] = json.dumps(True)
            await txn.handle.replace(
                CATEGORY_REV_LIST,
                rev_reg_def_id,
                value_json=value,
                tags=tags,
            )
            await txn.commit()

    async def get_pending_revocations(self, rev_reg_def_id: str) -> List[int]:
        """Retrieve the list of credential revocation ids pending revocation."""
        async with self.profile.session() as session:
            entry = await session.handle.fetch(CATEGORY_REV_LIST, rev_reg_def_id)
            if not entry:
                return []

            return entry.value_json["pending"] or []

    async def clear_pending_revocations(
        self,
        txn: ProfileSession,
        rev_reg_def_id: str,
        crid_mask: Optional[Sequence[int]] = None,
    ):
        """Clear pending revocations."""
        if not isinstance(txn, AskarAnoncredsProfileSession):
            raise ValueError("Askar wallet required")

        entry = await txn.handle.fetch(
            CATEGORY_REV_LIST,
            rev_reg_def_id,
            for_update=True,
        )

        if not entry:
            raise AnonCredsRevocationError(
                "Revocation list with id {rev_reg_def_id} not found"
            )

        value = entry.value_json
        if crid_mask is None:
            value["pending"] = None
        else:
            value["pending"] = set(value["pending"]) - set(crid_mask)

        tags = entry.tags
        tags["pending"] = json.dumps(False)
        await txn.handle.replace(
            CATEGORY_REV_LIST,
            rev_reg_def_id,
            value_json=value,
            tags=tags,
        )

    async def set_tails_file_public_uri(self, rev_reg_id, tails_public_uri):
        """Update Revocation Registry tails file public uri."""
        pass

    async def set_rev_reg_state(self, rev_reg_id, state):
        """Update Revocation Registry state."""
        pass
