"""Revocation through ledger agnostic AnonCreds interface."""

import asyncio
import hashlib
import http
import logging
import os
import time
from collections.abc import Mapping
from pathlib import Path
from typing import List, NamedTuple, Optional, Tuple
from urllib.parse import urlparse

import base58
from anoncreds import (
    AnoncredsError,
    Credential,
    CredentialRevocationConfig,
    RevocationRegistryDefinition,
    RevocationRegistryDefinitionPrivate,
    RevocationStatusList,
    W3cCredential,
)
from aries_askar import AskarErrorCode, Entry
from aries_askar.error import AskarError
from requests import RequestException, Session
from uuid_utils import uuid4

from ...askar.profile_anon import AskarAnonCredsProfileSession
from ...core.error import BaseError
from ...core.event_bus import Event, EventBus
from ...core.profile import Profile, ProfileSession
from ...database_manager.db_errors import DBError
from ...kanon.profile_anon_kanon import KanonAnonCredsProfileSession
from ...tails.anoncreds_tails_server import AnonCredsTailsServer
from ..constants import (
    CATEGORY_CRED_DEF,
    CATEGORY_CRED_DEF_PRIVATE,
    CATEGORY_REV_LIST,
    CATEGORY_REV_REG_DEF,
    CATEGORY_REV_REG_DEF_PRIVATE,
    STATE_FINISHED,
)
from ..error_messages import ANONCREDS_PROFILE_REQUIRED_MSG
from ..events import (
    FIRST_REGISTRY_TAG,
    RevListCreateRequestedEvent,
    RevListCreateResponseEvent,
    RevListFinishedEvent,
    RevListStoreRequestedEvent,
    RevListStoreResponseEvent,
    RevRegActivationRequestedEvent,
    RevRegActivationResponseEvent,
    RevRegDefCreateRequestedEvent,
    RevRegDefCreateResponseEvent,
    RevRegDefFinishedEvent,
    RevRegDefStoreRequestedEvent,
    RevRegDefStoreResponseEvent,
    RevRegFullDetectedEvent,
    RevRegFullHandlingResponseEvent,
)
from ..issuer import AnonCredsIssuer
from ..models.credential_definition import CredDef
from ..models.revocation import (
    RevList,
    RevListResult,
    RevListState,
    RevRegDef,
    RevRegDefResult,
    RevRegDefState,
)
from ..registry import AnonCredsRegistry
from ..util import indy_client_dir
from .auto_recovery import generate_request_id

LOGGER = logging.getLogger(__name__)

REVOCATION_REGISTRY_CREATION_TIMEOUT = float(
    os.getenv("REVOCATION_REGISTRY_CREATION_TIMEOUT", "60.0")
)

REV_REG_DEF_ID_NOT_FOUND_MSG = "Revocation registry definition id or job id not found"


class AnonCredsRevocationError(BaseError):
    """Generic revocation error."""


class AnonCredsRevocationRegistryFullError(AnonCredsRevocationError):
    """Revocation registry is full when issuing a new credential."""


class RevokeResult(NamedTuple):
    """RevokeResult."""

    prev: RevList
    curr: Optional[RevList] = None
    revoked: Optional[list[int]] = None
    failed: Optional[list[str]] = None


class AnonCredsRevocation:
    """Revocation registry operations manager."""

    def __init__(self, profile: Profile) -> None:
        """Initialize an AnonCredsRevocation instance.

        Args:
            profile: The active profile instance

        """
        self._profile = profile
        self._profile_validated = False  # Lazy validation of profile backend

    @property
    def profile(self) -> Profile:
        """Accessor for the profile instance."""
        if not self._profile_validated:
            if not isinstance(self._profile, Profile) or not self._profile.is_anoncreds:
                raise ValueError(ANONCREDS_PROFILE_REQUIRED_MSG)
            self._profile_validated = True

        return self._profile

    async def notify(self, event: Event) -> None:
        """Emit an event on the event bus."""
        event_bus = self.profile.inject(EventBus)
        await event_bus.notify(self.profile, event)

    async def _finish_registration(
        self,
        txn: ProfileSession,
        category: str,
        job_id: str,
        registered_id: str,
        *,
        state: Optional[str] = None,
    ) -> Entry:
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

    async def emit_create_revocation_registry_definition_event(
        self,
        issuer_id: str,
        cred_def_id: str,
        registry_type: str,
        tag: str,
        max_cred_num: int,
        options: Optional[dict] = None,
    ) -> None:
        """Emit event to request creation and registration of a new revocation registry.

        Args:
            issuer_id (str): issuer identifier
            cred_def_id (str): credential definition identifier
            registry_type (str): revocation registry type
            tag (str): revocation registry tag
            max_cred_num (int): maximum number of credentials supported
            options (dict): revocation registry options

        """
        options = options or {}
        LOGGER.info(
            "Emitting create revocation registry definition event for issuer: %s, "
            "cred_def_id: %s, registry_type: %s, tag: %s, max_cred_num: %s. "
            "request_id: %s, correlation_id: %s",
            issuer_id,
            cred_def_id,
            registry_type,
            tag,
            max_cred_num,
            options.get("request_id"),
            options.get("correlation_id"),
        )
        event = RevRegDefCreateRequestedEvent.with_payload(
            issuer_id=issuer_id,
            cred_def_id=cred_def_id,
            registry_type=registry_type,
            tag=tag,
            max_cred_num=max_cred_num,
            options=options,
        )
        await self.notify(event)

    async def create_and_register_revocation_registry_definition(
        self,
        issuer_id: str,
        cred_def_id: str,
        registry_type: str,
        tag: str,
        max_cred_num: int,
        options: Optional[dict] = None,
    ) -> RevRegDefResult | str:
        """Create a new revocation registry and register on network.

        This method picks up the RevRegDefCreateRequestedEvent, performing the registry
        creation and registration, emitting success or failure events based on the result.

        Args:
            issuer_id (str): issuer identifier
            cred_def_id (str): credential definition identifier
            registry_type (str): revocation registry type
            tag (str): revocation registry tag
            max_cred_num (int): maximum number of credentials supported
            options (dict): revocation registry options

        Returns:
            RevRegDefResult: revocation registry definition result,
                or error message if failed.

        """
        options = options or {}
        LOGGER.debug(
            "Creating and registering revocation registry definition for issuer: %s, "
            "cred_def_id: %s, registry_type: %s, tag: %s, max_cred_num: %s. "
            "request_id: %s, correlation_id: %s",
            issuer_id,
            cred_def_id,
            registry_type,
            tag,
            max_cred_num,
            options.get("request_id"),
            options.get("correlation_id"),
        )
        retry_count = options.pop("retry_count", 0)

        try:
            # Validate credential definition exists
            async with self.profile.session() as session:
                cred_def = await session.handle.fetch(CATEGORY_CRED_DEF, cred_def_id)

            if not cred_def:
                raise AskarError(
                    AskarErrorCode.NOT_FOUND,
                    f"Credential definition {cred_def_id} not found for "
                    f"creating revocation registry {tag}",
                )

            # Create a directory for the tails file in the indy-client directory
            tails_dir = indy_client_dir("tails", create=True)

            # Method to create the revocation registry definition and private key
            def create_rev_reg_def() -> Tuple[
                RevocationRegistryDefinition, RevocationRegistryDefinitionPrivate
            ]:
                return RevocationRegistryDefinition.create(
                    cred_def_id,
                    cred_def.raw_value,
                    issuer_id,
                    tag,
                    registry_type,
                    max_cred_num,
                    tails_dir_path=tails_dir,
                )

            # Run the creation of the revocation registry definition in a thread pool
            # to avoid blocking the event loop
            (
                rev_reg_def,
                rev_reg_def_private,
            ) = await asyncio.get_event_loop().run_in_executor(None, create_rev_reg_def)

            rev_reg_def = RevRegDef.from_native(rev_reg_def)

            # Generate and set the public tails URI
            public_tails_uri = self.generate_public_tails_uri(rev_reg_def)
            rev_reg_def.value.tails_location = public_tails_uri

            # Upload tails file
            await self.upload_tails_file(rev_reg_def)

            # We want to store the private key now so we can recover it in case of failure
            # Example of failure and recovery scenario:
            # - Rev reg creation is requested, but agent terminates before it completes.
            # - Rev reg creation actually succeeded on the ledger, but the agent never
            #   got the response to emit next event, so on recovery, tries to recreate it.
            # - The ledger should return the existing rev reg, instead of recreating it.
            # We don't know the rev_reg_def_id until after registry creation, so to link
            # the rev reg with the private key, we can instead use the tails hash, which
            # is known, and then we recover the private key from storage using the tails
            # file hash of the returned RevRegDefResult

            # Store the private definition with temporary identifier to avoid losing it
            private_key_storage_id = self._get_private_key_storage_id(rev_reg_def)
            LOGGER.debug(
                "Storing private revocation registry definition with storage ID: %s",
                private_key_storage_id,
            )
            async with self.profile.session() as session:
                await session.handle.insert(
                    CATEGORY_REV_REG_DEF_PRIVATE,
                    private_key_storage_id,
                    rev_reg_def_private.to_json_buffer(),
                )

            # Register on network
            anoncreds_registry = self.profile.inject(AnonCredsRegistry)
            result = await anoncreds_registry.register_revocation_registry_definition(
                self.profile, rev_reg_def, options
            )

            # Emit success event, which passes info needed to trigger the store request
            LOGGER.info(
                "Emitting successful create rev reg def response event for rev reg def: "
                "rev reg def id: %s, cred_def_id: %s, registry_type: %s, tag: %s, "
                "max_cred_num: %s, issuer_id: %s. request_id: %s, correlation_id: %s",
                result.rev_reg_def_id,
                cred_def_id,
                registry_type,
                tag,
                max_cred_num,
                issuer_id,
                options.get("request_id"),
                options.get("correlation_id"),
            )

            event = RevRegDefCreateResponseEvent.with_payload(
                rev_reg_def_result=result,
                rev_reg_def=rev_reg_def,
                options=options,
            )
            await self.notify(event)

            return result
        except Exception as err:
            # Emit failure event with appropriate error message based on exception type
            should_retry = True
            if isinstance(err, AskarError):
                error_msg = f"Error retrieving credential definition: {str(err)}"
                if err.code == AskarErrorCode.NOT_FOUND:
                    should_retry = False
            elif isinstance(err, AnoncredsError):  # pragma: no cover
                error_msg = f"Error creating revocation registry: {str(err)}"
            else:  # pragma: no cover
                error_msg = f"Registry creation failed: {str(err)}"

            if "Resource already exists" in error_msg:
                should_retry = False

            error_msg += (
                f". Extra context: issuer_id: {issuer_id}, "
                f"cred_def_id: {cred_def_id}, registry_type: {registry_type}, "
                f"tag: {tag}, max_cred_num: {max_cred_num}, options: {options}"
            )

            LOGGER.warning(f"{error_msg}. Emitting failure event.")

            event = RevRegDefCreateResponseEvent.with_failure(
                error_msg=error_msg,
                should_retry=should_retry,
                retry_count=retry_count,
                issuer_id=issuer_id,
                cred_def_id=cred_def_id,
                registry_type=registry_type,
                tag=tag,
                max_cred_num=max_cred_num,
                options=options,
            )
            await self.notify(event)

            # Return error message for web response.
            # Don't raise, in order to avoid exception handling in auto revocation setup
            return error_msg

    async def emit_store_revocation_registry_definition_event(
        self,
        *,
        rev_reg_def: RevRegDef,
        rev_reg_def_result: RevRegDefResult,
        options: Optional[dict] = None,
    ) -> None:
        """Emit event to request storing revocation registry definition locally.

        Args:
            rev_reg_def_result (RevRegDefResult): revocation registry definition result
            rev_reg_def (RevRegDef): revocation registry definition
            options (dict): storage options

        """
        options = options or {}
        LOGGER.info(
            "Emitting store revocation registry definition event for rev_reg_def_id: %s, "
            "tag: %s. request_id: %s, correlation_id: %s",
            rev_reg_def_result.rev_reg_def_id,
            rev_reg_def.tag,
            options.get("request_id"),
            options.get("correlation_id"),
        )

        event = RevRegDefStoreRequestedEvent.with_payload(
            rev_reg_def=rev_reg_def,
            rev_reg_def_result=rev_reg_def_result,
            options=options,
        )
        await self.notify(event)

    async def handle_store_revocation_registry_definition_request(
        self,
        rev_reg_def_result: RevRegDefResult,
        options: Optional[dict] = None,
    ) -> None:
        """Handle storing revocation registry definition locally.

        If the tag is the first registry, then successful storage will trigger the
        creation of a backup registry.

        Args:
            rev_reg_def_result (RevRegDefResult): revocation registry definition result
            options (dict): storage options

        """
        options = options or {}
        retry_count = options.pop("retry_count", 0)
        rev_reg_def_state = rev_reg_def_result.revocation_registry_definition_state
        rev_reg_def = rev_reg_def_state.revocation_registry_definition
        tag = rev_reg_def.tag
        rev_reg_def_id = rev_reg_def_result.rev_reg_def_id

        LOGGER.debug(
            "Handling registry store request for rev_reg_def_id: %s, tag: %s. "
            "request_id: %s, correlation_id: %s",
            rev_reg_def_id,
            tag,
            options.get("request_id"),
            options.get("correlation_id"),
        )

        try:
            # Store locally
            await self.store_revocation_registry_definition(rev_reg_def_result, options)

            # Emit success event
            LOGGER.info(
                "Emitting rev-reg-def store response event for rev reg def id: %s, "
                "tag: %s. request_id: %s, correlation_id: %s",
                rev_reg_def_id,
                tag,
                options.get("request_id"),
                options.get("correlation_id"),
            )
            event = RevRegDefStoreResponseEvent.with_payload(
                rev_reg_def_id=rev_reg_def_id,
                rev_reg_def=rev_reg_def,
                rev_reg_def_result=rev_reg_def_result,
                tag=tag,
                options=options,
            )
            await self.notify(event)

        except Exception as err:
            # Emit failure event
            should_retry = True
            if isinstance(err, AnonCredsRevocationError):
                error_msg = str(err)
                if REV_REG_DEF_ID_NOT_FOUND_MSG in error_msg:
                    should_retry = False
            else:
                error_msg = f"Store operation failed: {str(err)}"

            error_msg += (
                f". Extra context: rev_reg_def_id: {rev_reg_def_id}, "
                f"tag: {tag}, options: {options}"
            )

            LOGGER.warning(f"{error_msg}. Emitting failure event.")

            event = RevRegDefStoreResponseEvent.with_failure(
                rev_reg_def_id=rev_reg_def_id,
                rev_reg_def=rev_reg_def,
                rev_reg_def_result=rev_reg_def_result,
                tag=tag,
                error_msg=error_msg,
                should_retry=should_retry,
                retry_count=retry_count,
                options=options,
            )
            await self.notify(event)

    async def store_revocation_registry_definition(
        self,
        result: RevRegDefResult,
        options: Optional[dict] = None,
    ) -> None:
        """Store a revocation registry definition.

        Args:
            result (RevRegDefResult): revocation registry definition result
            options (dict): storage options

        """
        options = options or {}
        identifier = result.job_id or result.rev_reg_def_id
        if not identifier:
            raise AnonCredsRevocationError(REV_REG_DEF_ID_NOT_FOUND_MSG)
        LOGGER.debug(
            "Storing revocation registry definition for rev_reg_def_id: %s, tag: %s. "
            "request_id: %s, correlation_id: %s",
            result.rev_reg_def_id,
            result.revocation_registry_definition_state.revocation_registry_definition.tag,
            options.get("request_id"),
            options.get("correlation_id"),
        )

        rev_reg_def = (
            result.revocation_registry_definition_state.revocation_registry_definition
        )
        rev_reg_def_state = result.revocation_registry_definition_state.state

        try:
            private_key_storage_id = self._get_private_key_storage_id(rev_reg_def)

            # Read the private definition from storage (stored immediately after creation)
            async with self.profile.session() as session:
                rev_reg_def_private_entry = await session.handle.fetch(
                    CATEGORY_REV_REG_DEF_PRIVATE, private_key_storage_id
                )

            if not rev_reg_def_private_entry:
                raise AnonCredsRevocationError(
                    "Private revocation registry definition "
                    f"not found for {private_key_storage_id}"
                )

            async with self.profile.transaction() as txn:
                await txn.handle.insert(
                    CATEGORY_REV_REG_DEF,
                    identifier,
                    rev_reg_def.to_json(),
                    tags={
                        "cred_def_id": rev_reg_def.cred_def_id,
                        "state": rev_reg_def_state,
                        "active": "false",
                    },
                )
                await txn.handle.insert(
                    CATEGORY_REV_REG_DEF_PRIVATE,
                    identifier,
                    rev_reg_def_private_entry.value,
                )
                await txn.handle.remove(
                    CATEGORY_REV_REG_DEF_PRIVATE, private_key_storage_id
                )
                LOGGER.debug(
                    "Removed rev reg def private %s from storage",
                    private_key_storage_id,
                )
                await txn.commit()
            LOGGER.debug("Revocation registry definition storage transaction committed")

            if result.revocation_registry_definition_state.state == STATE_FINISHED:
                await self.notify(
                    RevRegDefFinishedEvent.with_payload(
                        rev_reg_def_id=identifier,
                        rev_reg_def=rev_reg_def,
                        options=options,
                    )
                )
        except DBError as err:
            raise AnonCredsRevocationError(
                "Error storing revocation registry definition"
            ) from err

    async def finish_revocation_registry_definition(
        self, job_id: str, rev_reg_def_id: str, options: Optional[dict] = None
    ) -> None:
        """Mark a rev reg def as finished."""
        options = options or {}
        LOGGER.debug(
            "Finishing revocation registry definition job_id=%s, rev_reg_def_id=%s",
            job_id,
            rev_reg_def_id,
        )
        async with self.profile.transaction() as txn:
            await self._finish_registration(
                txn,
                CATEGORY_REV_REG_DEF,
                job_id,
                rev_reg_def_id,
                state=STATE_FINISHED,
            )
            await self._finish_registration(
                txn,
                CATEGORY_REV_REG_DEF_PRIVATE,
                job_id,
                rev_reg_def_id,
            )
            await txn.commit()

        options.pop("correlation_id", None)  # Remove correlation id for new request
        await self.emit_create_and_register_revocation_list_event(
            rev_reg_def_id=rev_reg_def_id,
            options=options,
        )

    async def get_created_revocation_registry_definitions(
        self,
        cred_def_id: Optional[str] = None,
        state: Optional[str] = None,
    ) -> list[str]:
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
        return [entry.name for entry in list(rev_reg_defs)]

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

    async def set_active_registry(self, rev_reg_def_id: str) -> None:
        """Mark a registry as active."""
        LOGGER.debug("Setting registry as active: %s", rev_reg_def_id)
        async with self.profile.transaction() as txn:
            entry = await txn.handle.fetch(
                CATEGORY_REV_REG_DEF,
                rev_reg_def_id,
                for_update=True,
            )
            if not entry:
                raise AnonCredsRevocationError(
                    f"{CATEGORY_REV_REG_DEF} with id {rev_reg_def_id} could not be found"
                )

            if entry.tags["active"] == "true":
                LOGGER.warning("Registry %s is already active", rev_reg_def_id)
                # NOTE If there are other registries set as active, we're not
                # clearing them if the one we want to be active is already
                # active. This probably isn't an issue.
                return

            cred_def_id = entry.tags["cred_def_id"]

            old_active_entries = await txn.handle.fetch_all(
                CATEGORY_REV_REG_DEF,
                {
                    "active": "true",
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
                tags["active"] = "false"
                await txn.handle.replace(
                    CATEGORY_REV_REG_DEF,
                    old_entry.name,
                    old_entry.value,
                    tags,
                )

            tags = entry.tags
            tags["active"] = "true"
            await txn.handle.replace(
                CATEGORY_REV_REG_DEF,
                rev_reg_def_id,
                value=entry.value,
                tags=tags,
            )
            await txn.commit()

        LOGGER.debug("Registry %s set as active", rev_reg_def_id)

    async def emit_create_and_register_revocation_list_event(
        self,
        rev_reg_def_id: str,
        options: Optional[dict] = None,
    ) -> None:
        """Emit event to request revocation list creation.

        Args:
            rev_reg_def_id (str): revocation registry definition ID
            options (dict): creation options

        """
        options = options or {}
        LOGGER.info(
            "Emitting create and register revocation list event for rev_reg_def_id: %s. "
            "request_id: %s, correlation_id: %s",
            rev_reg_def_id,
            options.get("request_id"),
            options.get("correlation_id"),
        )

        # Emit event to request revocation list creation
        event = RevListCreateRequestedEvent.with_payload(
            rev_reg_def_id=rev_reg_def_id, options=options
        )
        await self.notify(event)

    async def emit_store_revocation_list_event(
        self,
        rev_reg_def_id: str,
        result: RevListResult,
        options: Optional[dict] = None,
    ) -> None:
        """Emit event to request revocation list storage.

        Args:
            rev_reg_def_id (str): revocation registry definition ID
            result (RevListResult): revocation list result
            options (dict): storage options

        """
        options = options or {}
        LOGGER.info(
            "Emitting store revocation list event for rev_reg_def_id: %s. "
            "request_id: %s, correlation_id: %s",
            rev_reg_def_id,
            options.get("request_id"),
            options.get("correlation_id"),
        )

        # Emit event to request revocation list storage
        event = RevListStoreRequestedEvent.with_payload(
            rev_reg_def_id=rev_reg_def_id, result=result, options=options
        )
        await self.notify(event)

    async def wait_for_active_revocation_registry(self, cred_def_id: str) -> None:
        """Wait for revocation registry setup to complete.

        Polls for the creation of revocation registry definitions until we have
        the 1 active registry or timeout occurs.

        Args:
            cred_def_id: The credential definition ID

        Raises:
            TimeoutError: If timeout occurs before completion

        """
        LOGGER.debug(
            "Waiting for revocation setup completion for cred_def_id: %s", cred_def_id
        )

        expected_count = 1  # Active registry
        poll_interval = 0.5  # Poll every 500ms
        max_iterations = int(REVOCATION_REGISTRY_CREATION_TIMEOUT / poll_interval)
        registries = []

        for _iteration in range(max_iterations):
            try:
                # Check for finished revocation registry definitions
                async with self.profile.session() as session:
                    registries = await session.handle.fetch_all(
                        CATEGORY_REV_REG_DEF,
                        {"cred_def_id": cred_def_id, "active": "true"},
                    )

                current_count = len(registries)
                LOGGER.debug(
                    "Revocation setup progress for %s: %d/%d registries active",
                    cred_def_id,
                    current_count,
                    expected_count,
                )

                if current_count >= expected_count:
                    LOGGER.info(
                        "Revocation setup completed for cred_def_id: %s "
                        "(%d registries active)",
                        cred_def_id,
                        current_count,
                    )
                    return

            except Exception as e:
                LOGGER.warning(
                    "Error checking revocation setup progress for %s: %s", cred_def_id, e
                )
                # Continue polling despite errors - they might be transient

            await asyncio.sleep(poll_interval)  # Wait before next poll

        # Timeout occurred
        current_count = len(registries)

        raise TimeoutError(
            "Timeout waiting for revocation setup completion for credential definition "
            f"{cred_def_id}. Expected {expected_count} revocation registries, but "
            f"{current_count} were active within {REVOCATION_REGISTRY_CREATION_TIMEOUT} "
            "seconds. Note: Revocation registry creation may still be in progress in the "
            "background. You can check status using the revocation registry endpoints."
        )

    async def create_and_register_revocation_list(
        self, rev_reg_def_id: str, options: Optional[dict] = None
    ) -> RevListResult | str:
        """Handle revocation list creation request event.

        Args:
            rev_reg_def_id (str): revocation registry definition ID
            options (dict): creation options

        Returns:
            RevListResult: revocation list result, or error message if failed

        """
        options = options or {}
        retry_count = options.get("retry_count", 0)

        try:
            # Fetch revocation registry definition and private definition
            async with self.profile.session() as session:
                rev_reg_def_entry = await session.handle.fetch(
                    CATEGORY_REV_REG_DEF, rev_reg_def_id
                )
                rev_reg_def_private_entry = await session.handle.fetch(
                    CATEGORY_REV_REG_DEF_PRIVATE, rev_reg_def_id
                )

                # Ensure both rev reg definition and private definition are present
                missing_items = []
                if not rev_reg_def_entry:
                    missing_items.append("revocation registry definition")
                if not rev_reg_def_private_entry:
                    missing_items.append("revocation registry private definition")

                if missing_items:
                    raise AskarError(
                        AskarErrorCode.NOT_FOUND,
                        f"Revocation registry data not found: {', '.join(missing_items)}",
                    )

                # Fetch credential definition
                cred_def_id = rev_reg_def_entry.value_json["credDefId"]
                cred_def_entry = await session.handle.fetch(
                    CATEGORY_CRED_DEF, cred_def_id
                )
                if not cred_def_entry:
                    raise AskarError(
                        AskarErrorCode.NOT_FOUND,
                        f"Credential definition {cred_def_id} not found",
                    )

            # Deserialize rev reg def, private def, and cred def
            rev_reg_def = RevRegDef.deserialize(rev_reg_def_entry.value_json)
            rev_reg_def_private = RevocationRegistryDefinitionPrivate.load(
                rev_reg_def_private_entry.value_json
            )
            cred_def = CredDef.deserialize(cred_def_entry.value_json)

            # Add "first" flag before registering, so we have it in case of registry error
            options["first_registry"] = rev_reg_def.tag == FIRST_REGISTRY_TAG

            # TODO This is a little rough; stored tails location will have public uri
            rev_reg_def.value.tails_location = self.get_local_tails_path(rev_reg_def)

            rev_list = RevocationStatusList.create(
                cred_def.to_native(),
                rev_reg_def_id,
                rev_reg_def.to_native(),
                rev_reg_def_private,
                rev_reg_def.issuer_id,
            )

            # Perform the actual revocation list creation and registration
            anoncreds_registry = self.profile.inject(AnonCredsRegistry)
            result = await anoncreds_registry.register_revocation_list(
                self.profile, rev_reg_def, RevList.from_native(rev_list), options
            )

            if options.get("failed_to_upload", False):
                # ??? Why register revocation list if we already know tails upload failed?
                result.revocation_list_state.state = RevListState.STATE_FAILED

            # Emit success event with the result to trigger store request
            LOGGER.info(
                "Emitting successful create and register revocation list event for "
                "rev_reg_def_id: %s, tag: %s. request_id: %s, correlation_id: %s",
                rev_reg_def_id,
                rev_reg_def.tag,
                options.get("request_id"),
                options.get("correlation_id"),
            )
            event = RevListCreateResponseEvent.with_payload(
                rev_reg_def_id=rev_reg_def_id,
                rev_list_result=result,
                options=options,
            )
            await self.notify(event)
            return result
        except Exception as err:
            # Emit failure event with appropriate error message based on exception type
            should_retry = True
            if isinstance(err, AskarError):
                error_msg = f"Error retrieving records: {str(err)}"
                if err.code == AskarErrorCode.NOT_FOUND:
                    should_retry = False
            elif isinstance(err, AnoncredsError):  # pragma: no cover
                error_msg = f"Error creating revocation list: {str(err)}"
            else:  # pragma: no cover
                error_msg = f"Revocation list creation failed: {str(err)}"

            if "Resource already exists" in error_msg:
                should_retry = False

            error_msg += (
                f". Extra context: rev_reg_def_id: {rev_reg_def_id}, options: {options}"
            )

            LOGGER.warning(f"{error_msg}. Emitting failure event.")

            event = RevListCreateResponseEvent.with_failure(
                rev_reg_def_id=rev_reg_def_id,
                error_msg=error_msg,
                should_retry=should_retry,
                retry_count=retry_count,
                options=options,
            )
            await self.notify(event)

            # Return error message for web response.
            # Don't raise, in order to avoid exception handling in auto revocation setup
            return error_msg

    async def store_revocation_registry_list(
        self, result: RevListResult, options: Optional[dict] = None
    ) -> None:
        """Store a revocation registry list."""
        options = options or {}
        LOGGER.debug(
            "Storing revocation registry list for rev_reg_def_id: %s. "
            "request_id: %s, correlation_id: %s",
            result.rev_reg_def_id,
            options.get("request_id"),
            options.get("correlation_id"),
        )

        identifier = result.job_id or result.rev_reg_def_id
        if not identifier:
            raise AnonCredsRevocationError(REV_REG_DEF_ID_NOT_FOUND_MSG)

        rev_list = result.revocation_list_state.revocation_list
        try:
            async with self.profile.session() as session:
                await session.handle.insert(
                    CATEGORY_REV_LIST,
                    identifier,
                    value_json={
                        "rev_list": rev_list.serialize(),
                        # AnonCreds uses the 0 index internally
                        # and can't be used for a credential
                        "next_index": 1,
                        "pending": None,
                    },
                    tags={
                        "state": result.revocation_list_state.state,
                        "pending": "false",
                    },
                )
                LOGGER.info(
                    "Revocation list stored successfully for rev_reg_def_id: %s. "
                    "request_id: %s, correlation_id: %s",
                    rev_list.rev_reg_def_id,
                    options.get("request_id"),
                    options.get("correlation_id"),
                )

            if result.revocation_list_state.state == STATE_FINISHED:
                LOGGER.info(
                    "Revocation list state is 'finished', emitting event for "
                    "rev_reg_def_id: %s. request_id: %s, correlation_id: %s",
                    rev_list.rev_reg_def_id,
                    options.get("request_id"),
                    options.get("correlation_id"),
                )
                await self.notify(
                    RevListFinishedEvent.with_payload(
                        rev_list.rev_reg_def_id,
                        rev_list.revocation_list,
                        options,
                    )
                )
            else:
                LOGGER.warning(
                    "Revocation list state is '%s', not emitting finished event for "
                    "rev_reg_def_id: %s. Options: %s",
                    result.revocation_list_state.state,
                    rev_list.rev_reg_def_id,
                    options,
                )

        except DBError as err:
            raise AnonCredsRevocationError(
                "Error storing revocation registry list"
            ) from err

    async def handle_store_revocation_list_request(
        self,
        rev_reg_def_id: str,
        result: RevListResult,
        options: Optional[dict] = None,
    ) -> None:
        """Handle revocation list store request.

        Args:
            rev_reg_def_id (str): revocation registry definition ID
            result (RevListResult): revocation list result
            options (dict): storage options

        """
        options = options or {}
        retry_count = options.pop("retry_count", 0)

        try:
            # Store the revocation list
            await self.store_revocation_registry_list(result, options)

            # Emit success event
            LOGGER.info(
                "Emitting revocation list store response event for rev_reg_def_id: %s. "
                "request_id: %s, correlation_id: %s",
                rev_reg_def_id,
                options.get("request_id"),
                options.get("correlation_id"),
            )
            event = RevListStoreResponseEvent.with_payload(
                rev_reg_def_id=rev_reg_def_id,
                result=result,
                options=options,
            )
            await self.notify(event)

        except Exception as err:
            # Emit failure event
            should_retry = True
            if isinstance(err, AskarError):
                error_msg = f"Error storing revocation list: {str(err)}"
                if err.code == AskarErrorCode.NOT_FOUND:
                    should_retry = False
            else:
                error_msg = f"Revocation list store failed: {str(err)}"

            error_msg += (
                f". Extra context: rev_reg_def_id: {rev_reg_def_id}, options: {options}"
            )

            LOGGER.warning(f"{error_msg}. Emitting failure event.")

            event = RevListStoreResponseEvent.with_failure(
                rev_reg_def_id=rev_reg_def_id,
                result=result,
                error_msg=error_msg,
                should_retry=should_retry,
                retry_count=retry_count,
                options=options,
            )
            await self.notify(event)

    async def finish_revocation_list(
        self, job_id: str, rev_reg_def_id: str, revoked: list
    ) -> None:
        """Mark a revocation list as finished."""
        LOGGER.info(
            "Finishing revocation list job_id=%s, rev_reg_def_id=%s, revoked=%s",
            job_id,
            rev_reg_def_id,
            revoked,
        )
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
                LOGGER.debug("Revocation list finish transaction committed")
            else:
                LOGGER.debug("Existing list found, skipping registration finish")

        LOGGER.info(
            "Notifying about %d revoked creds for rev_reg_def_id: %s",
            len(revoked),
            rev_reg_def_id,
        )
        await self.notify(RevListFinishedEvent.with_payload(rev_reg_def_id, revoked))

    async def update_revocation_list(
        self,
        rev_reg_def_id: str,
        prev: RevList,
        curr: RevList,
        revoked: list[int],
        options: Optional[dict] = None,
    ) -> RevListResult:
        """Publish and update to a revocation list."""
        options = options or {}
        LOGGER.debug(
            "Updating revocation list for rev_reg_def_id=%s with %d revoked credentials",
            rev_reg_def_id,
            len(revoked),
        )

        try:
            async with self.profile.session() as session:
                rev_reg_def_entry = await session.handle.fetch(
                    CATEGORY_REV_REG_DEF, rev_reg_def_id
                )
        except DBError as err:
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
        except DBError as err:
            raise AnonCredsRevocationError("Error retrieving revocation list") from err

        if not rev_list_entry:
            raise AnonCredsRevocationError(
                f"Revocation list not found for id {rev_reg_def_id}"
            )

        rev_reg_def = RevRegDef.deserialize(rev_reg_def_entry.value_json)
        rev_list = RevList.deserialize(rev_list_entry.value_json["rev_list"])
        if rev_list.revocation_list != curr.revocation_list:
            raise AnonCredsRevocationError("Passed revocation list does not match stored")

        anoncreds_registry = self.profile.inject(AnonCredsRegistry)
        result = await anoncreds_registry.update_revocation_list(
            self.profile, rev_reg_def, prev, curr, revoked, options
        )

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
        except DBError as err:
            raise AnonCredsRevocationError(
                "Error saving updated revocation list"
            ) from err

        return result

    async def get_created_revocation_list(self, rev_reg_def_id: str) -> Optional[RevList]:
        """Return rev list from record in wallet."""
        try:
            async with self.profile.session() as session:
                rev_list_entry = await session.handle.fetch(
                    CATEGORY_REV_LIST, rev_reg_def_id
                )
        except DBError as err:
            raise AnonCredsRevocationError("Error retrieving revocation list") from err

        if rev_list_entry:
            return RevList.deserialize(rev_list_entry.value_json["rev_list"])

        return None

    async def get_revocation_lists_with_pending_revocations(
        self,
    ) -> list[str]:
        """Return a list of rev reg def ids with pending revocations."""
        try:
            async with self.profile.session() as session:
                rev_list_entries = await session.handle.fetch_all(
                    CATEGORY_REV_LIST,
                    {"pending": "true"},
                )
        except DBError as err:
            raise AnonCredsRevocationError("Error retrieving revocation list") from err

        if rev_list_entries:
            return [entry.name for entry in list(rev_list_entries)]

        return []

    async def retrieve_tails(self, rev_reg_def: RevRegDef) -> str:
        """Retrieve tails file from server."""
        # TODO: This method is not actually async, and should be
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
                    resp = req_session.get(rev_reg_def.value.tails_location, stream=True)
                    # Should this directly raise an Error?
                    if resp.status_code != http.HTTPStatus.OK:
                        LOGGER.warning(
                            f"Unexpected status code for tails file: {resp.status_code}"
                        )
                    for buf in resp.iter_content(chunk_size=buffer_size):
                        tails_file.write(buf)
                        file_hasher.update(buf)
                except RequestException as rx:
                    raise AnonCredsRevocationError(
                        f"Error retrieving tails file: {rx}"
                    ) from rx

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

    def _check_url(self, url: str) -> None:
        parsed = urlparse(url)
        if not (parsed.scheme and parsed.netloc and parsed.path):
            raise AnonCredsRevocationError(f"URI {url} is not a valid URL")

    def generate_public_tails_uri(self, rev_reg_def: RevRegDef) -> str:
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

    async def upload_tails_file(self, rev_reg_def: RevRegDef) -> None:
        """Upload the local tails file to the tails server."""
        tails_server = AnonCredsTailsServer()

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
    async def handle_full_registry_event(
        self,
        rev_reg_def_id: str,
        cred_def_id: str,
        options: Optional[dict] = None,
    ) -> None:
        """Handle the full registry process event.

        This method handles the full registry process by:
        1. Finding the backup registry that should become active
        2. Setting the current registry state to full
        3. Activating the backup registry (event-driven)
        4. Creating a new backup registry (event-driven)

        Args:
            rev_reg_def_id (str): revocation registry definition ID that is full
            cred_def_id (str): credential definition ID
            options (dict): handling options

        """
        options = options or {}
        LOGGER.debug(
            "Handling full registry event for cred def id: %s, rev reg def id: %s. "
            "request_id: %s, correlation_id: %s",
            cred_def_id,
            rev_reg_def_id,
            options.get("request_id"),
            options.get("correlation_id"),
        )
        retry_count = options.get("retry_count", 0)

        try:
            # Find the backup registry that should become active
            async with self.profile.session() as session:
                # First, get the active registry
                active_rev_reg_def = await session.handle.fetch(
                    CATEGORY_REV_REG_DEF, rev_reg_def_id
                )
                if not active_rev_reg_def:
                    raise AnonCredsRevocationError(
                        f"Active registry {rev_reg_def_id} not found"
                    )

                # Then, find the backup registry (finished and not active)
                rev_reg_defs = await session.handle.fetch_all(
                    CATEGORY_REV_REG_DEF,
                    {
                        "active": "false",
                        "cred_def_id": cred_def_id,
                        "state": RevRegDefState.STATE_FINISHED,
                    },
                    limit=1,
                )
                if not rev_reg_defs:
                    raise AnonCredsRevocationError(
                        "Error handling full registry. No backup registry available."
                    )

                backup_rev_reg_def_id = rev_reg_defs[0].name

            # Set the current registry state to full
            await self.set_rev_reg_state(rev_reg_def_id, RevRegDefState.STATE_FULL)

            LOGGER.info(
                "Registry %s state set to full, activating backup registry %s. "
                "cred_def_id: %s, request_id: %s, correlation_id: %s",
                rev_reg_def_id,
                backup_rev_reg_def_id,
                cred_def_id,
                options.get("request_id"),
                options.get("correlation_id"),
            )

            # Store context for later use in creating new backup after activation
            set_active_registry_options = options.copy()
            set_active_registry_options["cred_def_id"] = cred_def_id
            set_active_registry_options["old_rev_reg_def_id"] = rev_reg_def_id
            set_active_registry_options.pop("correlation_id", None)

            # Activate the backup registry (this will trigger creation of new backup)
            await self.emit_set_active_registry_event(
                rev_reg_def_id=backup_rev_reg_def_id,
                options=set_active_registry_options,
            )

            LOGGER.info(
                "Emitting full handling response event for rev_reg_def_id: %s. "
                "cred_def_id: %s, request_id: %s, correlation_id: %s",
                rev_reg_def_id,
                cred_def_id,
                options.get("request_id"),
                options.get("correlation_id"),
            )
            full_handling_response_event = RevRegFullHandlingResponseEvent.with_payload(
                old_rev_reg_def_id=rev_reg_def_id,
                new_active_rev_reg_def_id=backup_rev_reg_def_id,
                cred_def_id=cred_def_id,
                options=options,
            )
            await self.notify(full_handling_response_event)

        except Exception as err:
            # Emit failure event
            error_msg = (
                f"Full registry handling failed: {str(err)}. "
                f"Extra context: rev_reg_def_id: {rev_reg_def_id}, options: {options}"
            )

            LOGGER.warning(f"{error_msg}. Emitting failure event.")

            event = RevRegFullHandlingResponseEvent.with_failure(
                old_rev_reg_def_id=rev_reg_def_id,
                cred_def_id=cred_def_id,
                error_msg=error_msg,
                retry_count=retry_count,
                options=options,
            )
            await self.notify(event)

    async def decommission_registry(self, cred_def_id: str) -> list:
        """Decommission post-init registries and start the next registry generation."""
        active_reg = await self.get_or_create_active_registry(cred_def_id)

        # create new one and set active
        LOGGER.debug("Creating new registry to replace active one")
        new_reg = await asyncio.shield(
            self.create_and_register_revocation_registry_definition(
                issuer_id=active_reg.rev_reg_def.issuer_id,
                cred_def_id=active_reg.rev_reg_def.cred_def_id,
                registry_type=active_reg.rev_reg_def.type,
                tag=self._generate_backup_registry_tag(),
                max_cred_num=active_reg.rev_reg_def.value.max_cred_num,
            )
        )
        # set new as active...
        if new_reg:
            new_rev_reg_def_id = new_reg.rev_reg_def_id
            await self.set_active_registry(new_rev_reg_def_id)
        else:
            new_rev_reg_def_id = None
            LOGGER.warning("No new registry created while decommissioning registry")

        # decommission everything except init/wait
        async with self.profile.transaction() as txn:
            registries = await txn.handle.fetch_all(
                CATEGORY_REV_REG_DEF,
                {
                    "cred_def_id": cred_def_id,
                },
                for_update=True,
            )

            def filter_registries(registry: Entry) -> bool:
                return registry.tags.get("state") != RevRegDefState.STATE_WAIT

            recs = list(filter(filter_registries, registries))

            for rec in recs:
                if rec.name != new_rev_reg_def_id:
                    tags = rec.tags
                    tags["active"] = "false"
                    tags["state"] = RevRegDefState.STATE_DECOMMISSIONED
                    await txn.handle.replace(
                        CATEGORY_REV_REG_DEF,
                        rec.name,
                        rec.value,
                        tags,
                    )
            await txn.commit()
        # create a second one for backup, don't make it active
        LOGGER.debug("Creating backup registry")
        backup_reg = await asyncio.shield(
            self.create_and_register_revocation_registry_definition(
                issuer_id=active_reg.rev_reg_def.issuer_id,
                cred_def_id=active_reg.rev_reg_def.cred_def_id,
                registry_type=active_reg.rev_reg_def.type,
                tag=self._generate_backup_registry_tag(),
                max_cred_num=active_reg.rev_reg_def.value.max_cred_num,
            )
        )

        LOGGER.debug(
            "New registry = %s.\nBackup registry = %s.\nDecommissioned registries = %s",
            new_reg,
            backup_reg,
            recs,
        )
        return recs

    async def get_or_create_active_registry(self, cred_def_id: str) -> RevRegDefResult:
        """Get the active revocation registry for a given cred def id."""
        async with self.profile.session() as session:
            rev_reg_defs = await session.handle.fetch_all(
                CATEGORY_REV_REG_DEF,
                {
                    "cred_def_id": cred_def_id,
                    "active": "true",
                },
                limit=1,
            )

        if not rev_reg_defs:
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

    async def emit_full_registry_event(
        self, rev_reg_def_id: str, cred_def_id: str
    ) -> None:
        """Emit event to indicate full registry detected.

        Args:
            rev_reg_def_id (str): revocation registry definition ID that is full
            cred_def_id (str): credential definition ID

        """
        request_id = generate_request_id()
        LOGGER.info(
            "Emitting full registry event for cred def id: %s, rev reg def id: %s, "
            "request_id: %s",
            cred_def_id,
            rev_reg_def_id,
            request_id,
        )
        options = {"request_id": request_id}

        # Emit event to indicate full registry detected
        event = RevRegFullDetectedEvent.with_payload(
            rev_reg_def_id=rev_reg_def_id,
            cred_def_id=cred_def_id,
            options=options,
        )
        await self.notify(event)

    async def emit_set_active_registry_event(
        self,
        rev_reg_def_id: str,
        options: Optional[dict] = None,
    ) -> None:
        """Emit event to request registry activation.

        Args:
            rev_reg_def_id (str): revocation registry definition ID
            options (dict): activation options

        """
        options = options or {}
        LOGGER.info(
            "Emitting set active registry event for rev reg def id: %s. "
            "request_id: %s, correlation_id: %s",
            rev_reg_def_id,
            options.get("request_id"),
            options.get("correlation_id"),
        )

        event = RevRegActivationRequestedEvent.with_payload(
            rev_reg_def_id=rev_reg_def_id,
            options=options,
        )
        await self.notify(event)

    async def handle_activate_registry_request(
        self,
        rev_reg_def_id: str,
        options: Optional[dict] = None,
    ) -> None:
        """Handle registry activation request event.

        Args:
            rev_reg_def_id (str): revocation registry definition ID
            options (dict): activation options

        """
        options = options or {}
        retry_count = options.pop("retry_count", 0)

        try:
            # Perform registry activation
            await self.set_active_registry(rev_reg_def_id)

            # Emit success event
            LOGGER.info(
                "Emitting registry activation success response event for "
                "rev_reg_def_id: %s. request_id: %s, correlation_id: %s",
                rev_reg_def_id,
                options.get("request_id"),
                options.get("correlation_id"),
            )
            event = RevRegActivationResponseEvent.with_payload(
                rev_reg_def_id=rev_reg_def_id,
                options=options,
            )
            await self.notify(event)

        except Exception as err:
            # Emit failure event
            error_msg = (
                f"Registry activation failed: {str(err)}. "
                f"Extra context: rev_reg_def_id: {rev_reg_def_id}, options: {options}"
            )

            LOGGER.warning(f"{error_msg}. Emitting failure event.")

            event = RevRegActivationResponseEvent.with_failure(
                rev_reg_def_id=rev_reg_def_id,
                error_msg=error_msg,
                retry_count=retry_count,
                options=options,
            )
            await self.notify(event)

    # Credential Operations
    async def create_credential_w3c(
        self,
        w3c_credential_offer: dict,
        w3c_credential_request: dict,
        w3c_credential_values: dict,
        *,
        retries: int = 5,
    ) -> Tuple[str, str | None, str | None]:
        """Create a w3c_credential.

        Args:
            w3c_credential_offer: Credential Offer to create w3c_credential for
            w3c_credential_request: Credential request to create w3c_credential for
            w3c_credential_values: Values to go in w3c_credential
            retries: number of times to retry w3c_credential creation

        Returns:
            A tuple of created w3c_credential, revocation id, and the rev reg def id

        """
        return await self._create_credential_helper(
            w3c_credential_offer,
            w3c_credential_request,
            w3c_credential_values,
            W3cCredential,
            retries=retries,
        )

    async def _get_cred_def_objects(
        self, credential_definition_id: str
    ) -> tuple[Entry, Entry]:
        try:
            async with self.profile.session() as session:
                cred_def = await session.handle.fetch(
                    CATEGORY_CRED_DEF, credential_definition_id
                )
                cred_def_private = await session.handle.fetch(
                    CATEGORY_CRED_DEF_PRIVATE, credential_definition_id
                )
        except DBError as err:
            raise AnonCredsRevocationError(
                "Error retrieving credential definition"
            ) from err
        if not cred_def or not cred_def_private:
            raise AnonCredsRevocationError(
                "Credential definition not found for credential issuance"
            )
        return cred_def, cred_def_private

    def _check_and_get_attribute_raw_values(
        self, schema_attributes: List[str], credential_values: dict
    ) -> Mapping[str, str]:
        raw_values = {}
        for attribute in schema_attributes:
            # Ensure every attribute present in schema to be set.
            # Extraneous attribute names are ignored.
            try:
                credential_value = credential_values[attribute]
            except KeyError as err:
                raise AnonCredsRevocationError(
                    "Provided credential values are missing a value "
                    f"for the schema attribute '{attribute}'"
                ) from err

            raw_values[attribute] = str(credential_value)
        return raw_values

    async def _create_credential(
        self,
        credential_definition_id: str,
        schema_attributes: List[str],
        credential_offer: dict,
        credential_request: dict,
        credential_values: dict,
        credential_type: Credential | W3cCredential,
        rev_reg_def_id: Optional[str] = None,
        tails_file_path: Optional[str] = None,
    ) -> Tuple[str, str | None]:
        """Create a credential.

        Args:
            credential_definition_id: The credential definition ID
            schema_attributes: The schema attributes
            credential_offer: The credential offer
            credential_request: The credential request
            credential_values: The credential values
            credential_type: The credential type
            rev_reg_def_id: The revocation registry definition ID
            tails_file_path: The tails file path

        Returns:
            A tuple of created credential and revocation ID

        """

        def _handle_missing_entries(
            rev_list: Entry | None, rev_reg_def: Entry | None, rev_key: Entry | None
        ) -> None:
            if not rev_reg_def:
                raise AnonCredsRevocationError("Revocation registry definition not found")
            if not rev_key:
                raise AnonCredsRevocationError(
                    "Revocation registry definition private data not found"
                )
            if not rev_list:
                LOGGER.error("Revocation registry list not found for %s", rev_reg_def_id)
                raise AnonCredsRevocationError("Revocation registry list not found")

        revoc = None
        credential_revocation_id = None
        rev_list = None

        if rev_reg_def_id and tails_file_path:
            # We need to make sure the read, index increment, and write
            # operations are done in a transaction.
            # TODO: This isn't fully atomic in a clustered environment as the
            # read transaction may happen concurrently with another.
            async with self.profile.transaction() as txn:
                rev_reg_def = await txn.handle.fetch(CATEGORY_REV_REG_DEF, rev_reg_def_id)
                rev_list = await txn.handle.fetch(CATEGORY_REV_LIST, rev_reg_def_id)
                rev_key = await txn.handle.fetch(
                    CATEGORY_REV_REG_DEF_PRIVATE, rev_reg_def_id
                )

                _handle_missing_entries(rev_list, rev_reg_def, rev_key)

                rev_list_value_json = rev_list.value_json
                rev_list_tags = rev_list.tags

                # If the rev_list state is failed then the tails file was never uploaded,
                # try to upload it now and finish the revocation list
                if rev_list_tags.get("state") == RevListState.STATE_FAILED:
                    await self.upload_tails_file(
                        RevRegDef.deserialize(rev_reg_def.value_json)
                    )
                    rev_list_tags["state"] = RevListState.STATE_FINISHED

                rev_reg_index = rev_list_value_json["next_index"]
                try:
                    rev_reg_def = RevocationRegistryDefinition.load(rev_reg_def.raw_value)
                    rev_list = RevocationStatusList.load(rev_list_value_json["rev_list"])
                except AnoncredsError as err:
                    raise AnonCredsRevocationError(
                        "Error loading revocation registry"
                    ) from err

                # NOTE: we increment the index ahead of time to keep the
                # transaction short. The revocation registry itself will NOT
                # be updated because we always use ISSUANCE_BY_DEFAULT.
                # If something goes wrong later, the index will be skipped.
                # FIXME - double check issuance type in case of upgraded wallet?
                if rev_reg_index > rev_reg_def.max_cred_num:
                    raise AnonCredsRevocationRegistryFullError(
                        "Revocation registry is full"
                    )
                rev_list_value_json["next_index"] = rev_reg_index + 1
                await txn.handle.replace(
                    CATEGORY_REV_LIST,
                    rev_reg_def_id,
                    value_json=rev_list_value_json,
                    tags=rev_list_tags,
                )
                await txn.commit()

            revoc = CredentialRevocationConfig(
                rev_reg_def,
                rev_key.raw_value,
                rev_list,
                rev_reg_index,
            )
            credential_revocation_id = str(rev_reg_index)

        cred_def, cred_def_private = await self._get_cred_def_objects(
            credential_definition_id
        )

        try:
            credential = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: credential_type.create(
                    cred_def=cred_def.raw_value,
                    cred_def_private=cred_def_private.raw_value,
                    cred_offer=credential_offer,
                    cred_request=credential_request,
                    attr_raw_values=self._check_and_get_attribute_raw_values(
                        schema_attributes, credential_values
                    ),
                    revocation_config=revoc,
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
    ) -> Tuple[str, str | None, str | None]:
        """Create a credential.

        Args:
            credential_offer: Credential Offer to create credential for
            credential_request: Credential request to create credential for
            credential_values: Values to go in credential
            revoc_reg_id: ID of the revocation registry
            retries: number of times to retry credential creation

        Returns:
            A tuple of created credential, revocation id, and the rev reg def id

        """
        return await self._create_credential_helper(
            credential_offer,
            credential_request,
            credential_values,
            Credential,
            retries=retries,
        )

    async def _create_credential_helper(
        self,
        credential_offer: dict,
        credential_request: dict,
        credential_values: dict,
        credential_type: Credential | W3cCredential,
        *,
        retries: int = 5,
    ) -> Tuple[str, str | None, str | None]:
        """Create a credential.

        Args:
            credential_offer: Credential Offer to create credential for
            credential_request: Credential request to create credential for
            credential_values: Values to go in credential
            credential_type: Credential or W3cCredential
            retries: number of times to retry credential creation

        Returns:
            A tuple of created credential, revocation id, and the rev reg def id

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
                try:
                    rev_reg_def_result = await self.get_or_create_active_registry(
                        cred_def_id
                    )
                except AnonCredsRevocationError:
                    # No active registry, try again
                    continue

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
                    credential_type,
                    rev_reg_def_id,
                    tails_file_path,
                )
            except AnonCredsRevocationError as err:
                LOGGER.warning(f"Failed to create credential: {err.message}, retrying")
                continue

            def _is_full_registry(
                rev_reg_def_result: RevRegDefResult, cred_rev_id: str
            ) -> bool:
                # if we wait until max cred num is reached, we are too late.
                return (
                    rev_reg_def_result.rev_reg_def.value.max_cred_num
                    <= int(cred_rev_id) + 1
                )

            if cred_rev_id and rev_reg_def_id and rev_reg_def_result:
                if _is_full_registry(rev_reg_def_result, cred_rev_id):
                    await self.emit_full_registry_event(rev_reg_def_id, cred_def_id)

            return cred_json, cred_rev_id, rev_reg_def_id

        raise AnonCredsRevocationError(
            f"Cred def '{cred_def_id}' revocation registry or list is in a bad state"
        )

    async def revoke_pending_credentials(
        self,
        revoc_reg_id: str,
        *,
        additional_crids: Optional[list[int]] = None,
        limit_crids: Optional[list[int]] = None,
    ) -> RevokeResult:
        """Revoke a set of credentials in a revocation registry.

        Args:
            revoc_reg_id: ID of the revocation registry
            additional_crids: list of additional credential indexes to revoke
            limit_crids: a list of credential indexes to limit revocation to
                If None, all pending revocations will be published.
                If given, the intersection of pending and limit crids will be published.

        Returns:
            Tuple with the update revocation list, list of cred rev ids not revoked

        """
        LOGGER.info(
            "Starting revocation process for registry %s with "
            "additional_crids=%s, limit_crids=%s",
            revoc_reg_id,
            additional_crids,
            limit_crids,
        )
        updated_list = None
        max_attempt = 5
        attempt = 0

        while True:
            attempt += 1
            LOGGER.debug("Revocation attempt %d/%d", attempt, max_attempt)
            if attempt >= max_attempt:
                LOGGER.error(
                    "Max attempts (%d) reached while trying to update registry %s",
                    max_attempt,
                    revoc_reg_id,
                )
                raise AnonCredsRevocationError(
                    "Repeated conflict attempting to update registry"
                )
            try:
                async with self.profile.session() as session:
                    LOGGER.debug("Fetching revocation registry data for %s", revoc_reg_id)
                    rev_reg_def_entry = await session.handle.fetch(
                        CATEGORY_REV_REG_DEF, revoc_reg_id
                    )
                    rev_list_entry = await session.handle.fetch(
                        CATEGORY_REV_LIST, revoc_reg_id
                    )
                    rev_reg_def_private_entry = await session.handle.fetch(
                        CATEGORY_REV_REG_DEF_PRIVATE, revoc_reg_id
                    )
            except DBError as err:
                LOGGER.error(
                    "Failed to retrieve revocation registry data for %s: %s",
                    revoc_reg_id,
                    str(err),
                )
                raise AnonCredsRevocationError(
                    "Error retrieving revocation registry"
                ) from err

            if (
                not rev_reg_def_entry
                or not rev_list_entry
                or not rev_reg_def_private_entry
            ):
                missing_data = []
                if not rev_reg_def_entry:
                    missing_data.append("revocation registry definition")
                if not rev_list_entry:
                    missing_data.append("revocation list")
                if not rev_reg_def_private_entry:
                    missing_data.append("revocation registry private definition")
                LOGGER.error(
                    "Missing required revocation registry data for %s: %s",
                    revoc_reg_id,
                    ", ".join(missing_data),
                )
                raise AnonCredsRevocationError(
                    f"Missing required revocation registry data: {' '.join(missing_data)}"
                )

            try:
                async with self.profile.session() as session:
                    cred_def_id = rev_reg_def_entry.value_json["credDefId"]
                    LOGGER.debug("Fetching credential definition %s", cred_def_id)
                    cred_def_entry = await session.handle.fetch(
                        CATEGORY_CRED_DEF, cred_def_id
                    )
            except DBError as err:
                LOGGER.error(
                    "Failed to retrieve credential definition %s: %s",
                    cred_def_id,
                    str(err),
                )
                raise AnonCredsRevocationError(
                    f"Error retrieving cred def {cred_def_id}"
                ) from err

            try:
                # TODO This is a little rough; stored tails location will have public uri
                # but library needs local tails location
                LOGGER.debug("Deserializing revocation registry data")
                rev_reg_def = RevRegDef.deserialize(rev_reg_def_entry.value_json)
                rev_reg_def.value.tails_location = self.get_local_tails_path(rev_reg_def)
                cred_def = CredDef.deserialize(cred_def_entry.value_json)
                rev_reg_def_private = RevocationRegistryDefinitionPrivate.load(
                    rev_reg_def_private_entry.value_json
                )
            except AnoncredsError as err:
                LOGGER.error(
                    "Failed to load revocation registry definition: %s", str(err)
                )
                raise AnonCredsRevocationError(
                    "Error loading revocation registry definition"
                ) from err

            rev_crids: set[int] = set()
            failed_crids: set[int] = set()
            max_cred_num = rev_reg_def.value.max_cred_num
            rev_info = rev_list_entry.value_json
            cred_revoc_ids: list[int] = (rev_info["pending"] or []) + (
                additional_crids or []
            )
            rev_list = RevList.deserialize(rev_info["rev_list"])

            LOGGER.info(
                "Processing %d credential revocation IDs for registry %s",
                len(cred_revoc_ids),
                revoc_reg_id,
            )

            for rev_id in cred_revoc_ids:
                if rev_id < 1 or rev_id > max_cred_num:
                    LOGGER.error(
                        "Skipping requested credential revocation "
                        "on rev reg id %s, cred rev id=%s not in range (1-%d)",
                        revoc_reg_id,
                        rev_id,
                        max_cred_num,
                    )
                    failed_crids.add(rev_id)
                elif rev_id >= rev_info["next_index"]:
                    LOGGER.warning(
                        "Skipping requested credential revocation "
                        "on rev reg id %s, cred rev id=%s not yet issued (next_index=%d)",
                        revoc_reg_id,
                        rev_id,
                        rev_info["next_index"],
                    )
                    failed_crids.add(rev_id)
                elif rev_list.revocation_list[rev_id] == 1:
                    LOGGER.warning(
                        "Skipping requested credential revocation "
                        "on rev reg id %s, cred rev id=%s already revoked",
                        revoc_reg_id,
                        rev_id,
                    )
                    failed_crids.add(rev_id)
                else:
                    rev_crids.add(rev_id)

            if not rev_crids:
                LOGGER.info(
                    "No valid credentials to revoke for registry %s", revoc_reg_id
                )
                break

            if limit_crids is None or limit_crids == []:
                skipped_crids = set()
            else:
                skipped_crids = rev_crids - set(limit_crids)
            rev_crids = rev_crids - skipped_crids

            LOGGER.info(
                "Revoking %d credentials, skipping %d credentials for registry %s",
                len(rev_crids),
                len(skipped_crids),
                revoc_reg_id,
            )

            try:
                LOGGER.debug("Updating revocation list with new revocations")
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
                LOGGER.error("Failed to update revocation registry: %s", str(err))
                raise AnonCredsRevocationError(
                    "Error updating revocation registry"
                ) from err

            try:
                async with self.profile.transaction() as txn:
                    LOGGER.debug("Saving updated revocation list")
                    rev_info_upd = await txn.handle.fetch(
                        CATEGORY_REV_LIST, revoc_reg_id, for_update=True
                    )
                    if not rev_info_upd:
                        LOGGER.warning(
                            "Revocation registry %s missing during update, skipping",
                            revoc_reg_id,
                        )
                        updated_list = None
                        break
                    tags = rev_info_upd.tags
                    rev_info_upd = rev_info_upd.value_json
                    if rev_info_upd != rev_info:
                        LOGGER.debug(
                            "Concurrent update detected for registry %s, retrying",
                            revoc_reg_id,
                        )
                        continue
                    rev_info_upd["rev_list"] = updated_list.to_dict()  # type: ignore[union-attr]
                    rev_info_upd["pending"] = (
                        list(skipped_crids) if skipped_crids else None
                    )
                    tags["pending"] = "true" if skipped_crids else "false"
                    await txn.handle.replace(
                        CATEGORY_REV_LIST,
                        revoc_reg_id,
                        value_json=rev_info_upd,
                        tags=tags,
                    )
                    await txn.commit()
                    LOGGER.info(
                        "Successfully updated revocation list for registry %s",
                        revoc_reg_id,
                    )
            except DBError as err:
                LOGGER.error("Failed to save revocation registry: %s", str(err))
                raise AnonCredsRevocationError(
                    "Error saving revocation registry"
                ) from err
            break

        revoked = list(rev_crids)
        failed = [str(rev_id) for rev_id in sorted(failed_crids)]

        result = RevokeResult(
            prev=rev_list,
            curr=RevList.from_native(updated_list) if updated_list else None,
            revoked=revoked,
            failed=failed,
        )
        LOGGER.info(
            "Completed revocation process for registry %s: %d revoked, %d failed",
            revoc_reg_id,
            len(revoked),
            len(failed),
        )
        return result

    async def mark_pending_revocations(self, rev_reg_def_id: str, *crids: int) -> None:
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
            tags["pending"] = "true"
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
        crid_mask: Optional[list[int]] = None,
    ) -> None:
        """Clear pending revocations."""
        # Accept both Askar and Kanon anoncreds sessions
        accepted = isinstance(
            txn, (AskarAnonCredsProfileSession, KanonAnonCredsProfileSession)
        )

        if not accepted:
            raise ValueError("AnonCreds wallet session required")

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
        tags["pending"] = "false"
        await txn.handle.replace(
            CATEGORY_REV_LIST,
            rev_reg_def_id,
            value_json=value,
            tags=tags,
        )

    async def set_tails_file_public_uri(
        self, rev_reg_id: str, tails_public_uri: str
    ) -> None:
        """Update Revocation Registry tails file public uri."""
        # TODO: Implement or remove
        pass

    async def set_rev_reg_state(self, rev_reg_id: str, state: str) -> RevRegDef:
        """Update Revocation Registry state."""
        try:
            async with self.profile.transaction() as txn:
                # Fetch the revocation registry definition entry
                rev_reg_def_entry = await txn.handle.fetch(
                    CATEGORY_REV_REG_DEF, rev_reg_id, for_update=True
                )

                if not rev_reg_def_entry:
                    raise AnonCredsRevocationError(
                        f"Revocation registry definition not found for id {rev_reg_id}"
                    )

                # Update the state in the tags
                tags = rev_reg_def_entry.tags
                tags["state"] = state

                # Replace the entry with updated tags
                await txn.handle.replace(
                    CATEGORY_REV_REG_DEF,
                    rev_reg_id,
                    value=rev_reg_def_entry.value,
                    tags=tags,
                )

                await txn.commit()
        except AskarError as err:
            raise AnonCredsRevocationError(
                f"Error updating revocation registry state: {err}"
            ) from err

        LOGGER.debug("Set registry %s state: %s", rev_reg_id, state)
        return RevRegDef.deserialize(rev_reg_def_entry.value_json)

    def _generate_backup_registry_tag(self) -> str:
        """Generate a unique tag for a backup registry."""
        return str(uuid4())

    def _get_private_key_storage_id(self, rev_reg_def: RevRegDef) -> str:
        """Get the private key storage identifier for a revocation registry definition."""
        return f"rev_reg_def_private_{rev_reg_def.value.tails_hash}"
