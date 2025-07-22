"""Automated setup process for AnonCreds credential definitions with revocation."""

import asyncio
import logging
from abc import ABC, abstractmethod

from acapy_agent.anoncreds.issuer import STATE_FINISHED
from acapy_agent.protocols.endorse_transaction.v1_0.util import is_author_role

from ..anoncreds.revocation import AnonCredsRevocation, AnonCredsRevocationError
from ..core.event_bus import EventBus
from ..core.profile import Profile
from ..revocation.util import notify_revocation_published_event
from ..storage.type import (
    RECORD_TYPE_REV_LIST_CREATE_EVENT,
    RECORD_TYPE_REV_LIST_STORE_EVENT,
    RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
    RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
    RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
    RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
    RECORD_TYPE_TAILS_UPLOAD_EVENT,
)
from .event_storage import (
    EventStorageManager,
    generate_correlation_id,
    serialize_event_payload,
)
from .events import (
    FIRST_REGISTRY_TAG,
    CredDefFinishedEvent,
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
    TailsUploadRequestedEvent,
    TailsUploadResponseEvent,
)
from .models.revocation import GetRevListResult, RevListResult, RevListState
from .registry import AnonCredsRegistry

LOGGER = logging.getLogger(__name__)


class AnonCredsRevocationSetupManager(ABC):
    """Base class for automated setup of revocation."""

    @abstractmethod
    def register_events(self, event_bus: EventBus):
        """Event registration."""


class DefaultRevocationSetup(AnonCredsRevocationSetupManager):
    """Manager for automated setup of revocation support.

    This manager models a state machine for the revocation setup process where
    the transitions are triggered by the `finished` event of the previous
    artifact. The state machine is as follows:

    [*] --> Cred Def
    Cred Def --> Rev Reg Def
    Rev Reg Def --> Rev List
    Rev List --> [*]

    This implementation of an AnonCredsRevocationSetupManager will create two
    revocation registries for each credential definition supporting revocation;
    one that is active and one that is pending. When the active registry fills,
    the pending registry will be activated and a new pending registry will be
    created. This will continue indefinitely.

    This hot-swap approach to revocation registry management allows for
    issuance operations to be performed without a delay for registry
    creation.
    """

    REGISTRY_TYPE = "CL_ACCUM"
    MAX_RETRY_COUNT = 3

    def __init__(self):
        """Init manager."""

    def _clean_options_for_new_request(self, options: dict) -> dict:
        """Clean options for new request by removing correlation_id.

        Each new request should have a unique correlation_id. When transitioning
        from one successful operation to the next new operation, we need to remove
        the correlation_id so that the next operation generates its own unique
        correlation_id.

        Args:
            options (dict): Original options dictionary

        Returns:
            dict: Cleaned options dictionary without correlation_id
        """
        cleaned_options = options.copy()
        cleaned_options.pop("correlation_id", None)
        return cleaned_options

    def register_events(self, event_bus: EventBus) -> None:
        """Register event listeners."""
        # On cred def, request creation and registration of a revocation registry
        event_bus.subscribe(CredDefFinishedEvent.event_topic, self.on_cred_def)

        # On registry create requested, create and register a revocation registry
        event_bus.subscribe(
            RevRegDefCreateRequestedEvent.event_topic, self.on_registry_create_requested
        )
        # On registry create response, emit event to store the revocation registry
        event_bus.subscribe(
            RevRegDefCreateResponseEvent.event_topic, self.on_registry_create_response
        )

        # On registry store requested, store the revocation registry
        event_bus.subscribe(
            RevRegDefStoreRequestedEvent.event_topic, self.on_registry_store_requested
        )
        # On store success, emit rev reg finished event, and requests backup registry
        event_bus.subscribe(
            RevRegDefStoreResponseEvent.event_topic, self.on_registry_store_response
        )

        # Rev list finished event will notify the issuer of successful revocations
        event_bus.subscribe(RevListFinishedEvent.event_topic, self.on_rev_list_finished)

        # On rev reg def finished, emit tails upload request event
        event_bus.subscribe(RevRegDefFinishedEvent.event_topic, self.on_rev_reg_def)

        # On tails upload requested, upload tails file
        event_bus.subscribe(
            TailsUploadRequestedEvent.event_topic, self.on_tails_upload_requested
        )
        # On tails upload response, emit rev list create requested event
        event_bus.subscribe(
            TailsUploadResponseEvent.event_topic, self.on_tails_upload_response
        )

        # On rev list create requested, create and register a revocation list
        event_bus.subscribe(
            RevListCreateRequestedEvent.event_topic, self.on_rev_list_create_requested
        )
        # On successful rev list creation, emit store rev list request event
        event_bus.subscribe(
            RevListCreateResponseEvent.event_topic, self.on_rev_list_create_response
        )

        # On rev list store requested, store the revocation list
        event_bus.subscribe(
            RevListStoreRequestedEvent.event_topic, self.on_rev_list_store_requested
        )
        # On store success, emit set active registry event, if it is the first registry
        event_bus.subscribe(
            RevListStoreResponseEvent.event_topic, self.on_rev_list_store_response
        )

        # On set active registry requested, set the active registry
        event_bus.subscribe(
            RevRegActivationRequestedEvent.event_topic,
            self.on_registry_activation_requested,
        )
        # On successful registry activation, this completes the revocation setup
        event_bus.subscribe(
            RevRegActivationResponseEvent.event_topic,
            self.on_registry_activation_response,
        )

        event_bus.subscribe(
            RevRegFullDetectedEvent.event_topic,
            self.on_registry_full_detected,
        )
        event_bus.subscribe(
            RevRegFullHandlingResponseEvent.event_topic,
            self.on_registry_full_handling_response,
        )

    async def on_cred_def(self, profile: Profile, event: CredDefFinishedEvent) -> None:
        """Handle cred def finished."""
        payload = event.payload

        if payload.support_revocation:
            revoc = AnonCredsRevocation(profile)
            # Emit event to request creation and registration of a revocation registry
            # This automates the creation of a backup registry and accompanying resources
            await revoc.emit_create_revocation_registry_definition_event(
                issuer_id=payload.issuer_id,
                cred_def_id=payload.cred_def_id,
                registry_type=self.REGISTRY_TYPE,
                max_cred_num=payload.max_cred_num,
                tag=FIRST_REGISTRY_TAG,
                options=self._clean_options_for_new_request(payload.options),
            )

    async def on_registry_create_requested(  # ✅
        self, profile: Profile, event: RevRegDefCreateRequestedEvent
    ) -> None:
        """Handle registry creation request."""
        payload = event.payload
        revoc = AnonCredsRevocation(profile)

        # Check if this is a retry with existing correlation_id
        correlation_id = payload.options.get("correlation_id")
        if not correlation_id:
            # Generate new correlation_id for new requests
            correlation_id = generate_correlation_id()

            # Persist the request event only for new requests
            async with profile.session() as session:
                event_storage = EventStorageManager(session)
                await event_storage.store_event_request(
                    event_type=RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
                    event_data=serialize_event_payload(payload),
                    correlation_id=correlation_id,
                    options=payload.options,
                )

        LOGGER.debug(
            "Handling registry creation request for cred_def_id: %s, tag: %s, "
            "correlation_id: %s",
            payload.cred_def_id,
            payload.tag,
            correlation_id,
        )

        # Store correlation_id in options for response tracking
        options_with_correlation = payload.options.copy()
        options_with_correlation["correlation_id"] = correlation_id

        await asyncio.shield(
            revoc.create_and_register_revocation_registry_definition(
                issuer_id=payload.issuer_id,
                cred_def_id=payload.cred_def_id,
                registry_type=payload.registry_type,
                tag=payload.tag,
                max_cred_num=payload.max_cred_num,
                options=options_with_correlation,
            )
        )

    async def on_registry_create_response(
        self, profile: Profile, event: RevRegDefCreateResponseEvent
    ) -> None:
        """Handle registry creation response."""
        payload = event.payload

        # Update the persisted event with response information
        correlation_id = payload.options.get("correlation_id")
        if correlation_id:
            async with profile.session() as session:
                event_storage = EventStorageManager(session)
                if payload.failure:
                    await event_storage.update_event_response(
                        event_type=RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
                        correlation_id=correlation_id,
                        success=False,
                        response_data=serialize_event_payload(payload),
                        error_msg=payload.failure.error_info.error_msg,
                    )
                else:
                    await event_storage.update_event_response(
                        event_type=RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
                        correlation_id=correlation_id,
                        success=True,
                        response_data=serialize_event_payload(payload),
                    )
        else:
            LOGGER.warning("No correlation_id found for rev reg def create response")

        if payload.failure:
            # Handle failure with full type safety
            failure = payload.failure
            error_info = failure.error_info

            registry_type_name = (
                "initial" if failure.tag == FIRST_REGISTRY_TAG else "backup"
            )

            LOGGER.warning(
                "%s registry creation failed for cred_def_id: %s, error: %s",
                registry_type_name.title(),
                failure.cred_def_id,
                error_info.error_msg,
            )

            # Check if resource already exists; recover by fetching existing registry
            if "Resource already exists" in error_info.error_msg:
                LOGGER.error(
                    "Resource already exists for %s registry, "
                    "attempting to fetch existing resource",
                    registry_type_name,
                )

                # TODO: Implement recovery

            # Handle retry with structured data
            if error_info.should_retry and error_info.retry_count < self.MAX_RETRY_COUNT:
                LOGGER.info(
                    "Retrying %s registry creation, attempt %d",
                    registry_type_name,
                    error_info.retry_count + 1,
                )

                new_options = payload.options.copy()
                new_options["retry_count"] = error_info.retry_count + 1

                revoc = AnonCredsRevocation(profile)

                await revoc.emit_create_revocation_registry_definition_event(
                    issuer_id=failure.issuer_id,
                    cred_def_id=failure.cred_def_id,
                    registry_type=failure.registry_type,
                    tag=failure.tag,
                    max_cred_num=failure.max_cred_num,
                    options=new_options,
                )
            else:
                # Not retryable, so notify issuer about failure
                LOGGER.error(
                    "%s %s registry creation for cred def: %s",
                    "Max retries exceeded for"
                    if error_info.should_retry
                    else "Won't retry",
                    registry_type_name,
                    failure.cred_def_id,
                )
                # Mark the event as completed since we won't retry
                if correlation_id:
                    async with profile.session() as session:
                        event_storage = EventStorageManager(session)
                        await event_storage.mark_event_completed(
                            event_type=RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
                            correlation_id=correlation_id,
                        )
                # TODO: Implement notification to issuer about failure
        else:
            # Handle success - emit store request event
            revoc = AnonCredsRevocation(profile)
            await revoc.emit_store_revocation_registry_definition_event(
                rev_reg_def=payload.rev_reg_def,
                rev_reg_def_result=payload.rev_reg_def_result,
                options=self._clean_options_for_new_request(payload.options),
            )

    async def on_registry_store_requested(
        self, profile: Profile, event: RevRegDefStoreRequestedEvent
    ) -> None:
        """Handle registry store request."""
        payload = event.payload
        revoc = AnonCredsRevocation(profile)

        # Check if this is a retry with existing correlation_id
        correlation_id = payload.options.get("correlation_id")
        if not correlation_id:
            # Generate new correlation_id for new requests
            correlation_id = generate_correlation_id()

            # Persist the request event only for new requests
            async with profile.session() as session:
                event_storage = EventStorageManager(session)
                await event_storage.store_event_request(
                    event_type=RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
                    event_data=serialize_event_payload(payload),
                    correlation_id=correlation_id,
                    options=payload.options,
                )

        # Store correlation_id in options for response tracking
        options_with_correlation = payload.options.copy()
        options_with_correlation["correlation_id"] = correlation_id

        await revoc.handle_store_revocation_registry_definition_request(
            rev_reg_def_result=payload.rev_reg_def_result,
            options=options_with_correlation,
        )

    async def on_registry_store_response(
        self, profile: Profile, event: RevRegDefStoreResponseEvent
    ) -> None:
        """Handle registry store response."""
        payload = event.payload

        # Update the persisted event with response information
        correlation_id = payload.options.get("correlation_id")
        if correlation_id:
            async with profile.session() as session:
                event_storage = EventStorageManager(session)
                if payload.failure:
                    await event_storage.update_event_response(
                        event_type=RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
                        correlation_id=correlation_id,
                        success=False,
                        response_data=serialize_event_payload(payload),
                        error_msg=payload.failure.error_info.error_msg,
                    )
                else:
                    await event_storage.update_event_response(
                        event_type=RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
                        correlation_id=correlation_id,
                        success=True,
                        response_data=serialize_event_payload(payload),
                    )
        else:
            LOGGER.warning("No correlation_id found for rev reg def store response")

        if payload.failure:
            # Handle failure
            failure = payload.failure
            error_info = failure.error_info

            LOGGER.warning(
                "Registry store failed for: %s, tag: %s, error: %s",
                payload.rev_reg_def_id,
                payload.tag,
                error_info.error_msg,
            )

            # Implement retry logic
            if error_info.should_retry and error_info.retry_count < self.MAX_RETRY_COUNT:
                LOGGER.info(
                    "Retrying registry store, attempt %d", error_info.retry_count + 1
                )

                new_options = payload.options.copy()
                new_options["retry_count"] = error_info.retry_count + 1

                revoc = AnonCredsRevocation(profile)
                await revoc.handle_store_revocation_registry_definition_request(
                    rev_reg_def_result=payload.rev_reg_def_result,
                    options=new_options,
                )
            else:
                LOGGER.error(
                    "%s registry store for: %s, tag: %s",
                    "Max retries exceeded for"
                    if error_info.should_retry
                    else "Won't retry",
                    payload.rev_reg_def_id,
                    payload.tag,
                )
                # Mark the event as completed since we won't retry
                if correlation_id:
                    async with profile.session() as session:
                        event_storage = EventStorageManager(session)
                        await event_storage.mark_event_completed(
                            event_type=RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
                            correlation_id=correlation_id,
                        )
                # TODO: Implement notification to issuer about failure
        else:
            # Handle success
            LOGGER.info(
                "Registry store succeeded for: %s, tag: %s",
                payload.rev_reg_def_id,
                payload.tag,
            )

            # Mark the event as completed on success
            if correlation_id:
                async with profile.session() as session:
                    event_storage = EventStorageManager(session)
                    await event_storage.mark_event_completed(
                        event_type=RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
                        correlation_id=correlation_id,
                    )

            # Emit finished event
            revoc = AnonCredsRevocation(profile)
            state = payload.rev_reg_def_result.revocation_registry_definition_state.state
            if state == STATE_FINISHED:
                await revoc.emit_rev_reg_def_finished_event(
                    rev_reg_def_id=payload.rev_reg_def_id,
                    rev_reg_def=payload.rev_reg_def,
                    options=payload.options,
                )
            else:
                LOGGER.warning(
                    "Revocation registry definition %s not finished; has state %s",
                    payload.rev_reg_def_id,
                    state,
                )

            # If this is the first registry, trigger creation of backup registry
            if payload.tag == FIRST_REGISTRY_TAG:
                LOGGER.info(
                    "First registry stored successfully, "
                    "requesting creation of backup registry for cred_def_id: %s",
                    payload.rev_reg_def.cred_def_id,
                )
                await revoc.emit_create_revocation_registry_definition_event(
                    issuer_id=payload.rev_reg_def.issuer_id,
                    cred_def_id=payload.rev_reg_def.cred_def_id,
                    registry_type=payload.rev_reg_def.type,
                    tag=revoc._generate_backup_registry_tag(),
                    max_cred_num=payload.rev_reg_def.value.max_cred_num,
                    options=self._clean_options_for_new_request(payload.options),
                )

    async def on_rev_reg_def(
        self, profile: Profile, event: RevRegDefFinishedEvent
    ) -> None:
        """Handle rev reg def finished."""
        payload = event.payload

        auto_create_revocation = True
        if is_author_role(profile):
            auto_create_revocation = profile.settings.get(
                "endorser.auto_create_rev_reg", False
            )

        if auto_create_revocation:
            revoc = AnonCredsRevocation(profile)
            try:
                await revoc.emit_upload_tails_file_event(
                    rev_reg_def_id=payload.rev_reg_def_id,
                    rev_reg_def=payload.rev_reg_def,
                    options=self._clean_options_for_new_request(payload.options),
                )
            except AnonCredsRevocationError as err:  # TODO: ensure this is implemented
                LOGGER.warning(f"Failed to upload tails file: {err}")
                payload.options["failed_to_upload"] = True

    async def on_tails_upload_requested(
        self, profile: Profile, event: TailsUploadRequestedEvent
    ) -> None:
        """Handle tails upload request."""
        payload = event.payload
        revoc = AnonCredsRevocation(profile)

        # Check if this is a retry with existing correlation_id
        correlation_id = payload.options.get("correlation_id")
        if not correlation_id:
            # Generate new correlation_id for new requests
            correlation_id = generate_correlation_id()

            # Persist the request event only for new requests
            async with profile.session() as session:
                event_storage = EventStorageManager(session)
                await event_storage.store_event_request(
                    event_type=RECORD_TYPE_TAILS_UPLOAD_EVENT,
                    event_data=serialize_event_payload(payload),
                    correlation_id=correlation_id,
                    options=payload.options,
                )

        LOGGER.debug(
            "Handling tails upload request for: %s, correlation_id: %s",
            payload.rev_reg_def_id,
            correlation_id,
        )

        # Store correlation_id in options for response tracking
        options_with_correlation = payload.options.copy()
        options_with_correlation["correlation_id"] = correlation_id

        await revoc.handle_tails_upload_request(
            rev_reg_def_id=payload.rev_reg_def_id,
            rev_reg_def=payload.rev_reg_def,
            options=options_with_correlation,
        )

    async def on_tails_upload_response(
        self, profile: Profile, event: TailsUploadResponseEvent
    ) -> None:
        """Handle tails upload response."""
        payload = event.payload

        # Update the persisted event with response information
        correlation_id = payload.options.get("correlation_id")
        if correlation_id:
            async with profile.session() as session:
                event_storage = EventStorageManager(session)
                if payload.failure:
                    await event_storage.update_event_response(
                        event_type=RECORD_TYPE_TAILS_UPLOAD_EVENT,
                        correlation_id=correlation_id,
                        success=False,
                        response_data=serialize_event_payload(payload),
                        error_msg=payload.failure.error_info.error_msg,
                    )
                else:
                    await event_storage.update_event_response(
                        event_type=RECORD_TYPE_TAILS_UPLOAD_EVENT,
                        correlation_id=correlation_id,
                        success=True,
                        response_data=serialize_event_payload(payload),
                    )
        else:
            LOGGER.warning("No correlation_id found for tails upload response")

        if payload.failure:
            # Handle failure
            failure = payload.failure
            error_info = failure.error_info

            LOGGER.error(
                "Tails upload failed for: %s, error: %s",
                payload.rev_reg_def_id,
                error_info.error_msg,
            )

            # Implement retry logic
            if error_info.retry_count < self.MAX_RETRY_COUNT:
                LOGGER.info(
                    "Retrying tails upload, attempt %d", error_info.retry_count + 1
                )

                new_options = payload.options.copy()
                new_options["retry_count"] = error_info.retry_count + 1

                revoc = AnonCredsRevocation(profile)
                await revoc.emit_upload_tails_file_event(
                    rev_reg_def_id=payload.rev_reg_def_id,
                    rev_reg_def=payload.rev_reg_def,
                    options=new_options,
                )
            else:
                LOGGER.error(
                    "Max retries exceeded for tails upload: %s", payload.rev_reg_def_id
                )
                # Mark the event as completed since we won't retry
                if correlation_id:
                    async with profile.session() as session:
                        event_storage = EventStorageManager(session)
                        await event_storage.mark_event_completed(
                            event_type=RECORD_TYPE_TAILS_UPLOAD_EVENT,
                            correlation_id=correlation_id,
                        )
                # TODO: Implement notification to issuer about failure
        else:
            # Handle success
            LOGGER.info("Tails upload succeeded for: %s", payload.rev_reg_def_id)

            # Mark the event as completed on success
            if correlation_id:
                async with profile.session() as session:
                    event_storage = EventStorageManager(session)
                    await event_storage.mark_event_completed(
                        event_type=RECORD_TYPE_TAILS_UPLOAD_EVENT,
                        correlation_id=correlation_id,
                    )

            # Request revocation list creation
            revoc = AnonCredsRevocation(profile)
            await revoc.emit_create_and_register_revocation_list_event(
                rev_reg_def_id=payload.rev_reg_def_id,
                options=self._clean_options_for_new_request(payload.options),
            )

    async def on_rev_list_create_requested(
        self, profile: Profile, event: RevListCreateRequestedEvent
    ) -> None:
        """Handle revocation list creation request."""
        payload = event.payload
        revoc = AnonCredsRevocation(profile)

        # Check if this is a retry with existing correlation_id
        correlation_id = payload.options.get("correlation_id")
        if not correlation_id:
            # Generate new correlation_id for new requests
            correlation_id = generate_correlation_id()

            # Persist the request event only for new requests
            async with profile.session() as session:
                event_storage = EventStorageManager(session)
                await event_storage.store_event_request(
                    event_type=RECORD_TYPE_REV_LIST_CREATE_EVENT,
                    event_data=serialize_event_payload(payload),
                    correlation_id=correlation_id,
                    options=payload.options,
                )

        LOGGER.debug(
            "Handling revocation list creation request for: %s, correlation_id: %s",
            payload.rev_reg_def_id,
            correlation_id,
        )

        # Store correlation_id in options for response tracking
        options_with_correlation = payload.options.copy()
        options_with_correlation["correlation_id"] = correlation_id

        await asyncio.shield(
            revoc.create_and_register_revocation_list(
                rev_reg_def_id=payload.rev_reg_def_id,
                options=options_with_correlation,
            )
        )

    async def on_rev_list_create_response(
        self, profile: Profile, event: RevListCreateResponseEvent
    ) -> None:
        """Handle revocation list creation response."""
        payload = event.payload

        # Update the persisted event with response information
        correlation_id = payload.options.get("correlation_id")
        if correlation_id:
            async with profile.session() as session:
                event_storage = EventStorageManager(session)
                if payload.failure:
                    await event_storage.update_event_response(
                        event_type=RECORD_TYPE_REV_LIST_CREATE_EVENT,
                        correlation_id=correlation_id,
                        success=False,
                        response_data=serialize_event_payload(payload),
                        error_msg=payload.failure.error_info.error_msg,
                    )
                else:
                    await event_storage.update_event_response(
                        event_type=RECORD_TYPE_REV_LIST_CREATE_EVENT,
                        correlation_id=correlation_id,
                        success=True,
                        response_data=serialize_event_payload(payload),
                    )
        else:
            LOGGER.warning("No correlation_id found for rev list create response")

        if payload.failure:
            # Handle failure
            failure = payload.failure
            error_info = failure.error_info

            LOGGER.error(
                "Revocation list creation failed for: %s, error: %s",
                payload.rev_reg_def_id,
                error_info.error_msg,
            )

            # Check if resource already exists and try to recover by fetching it
            if "Resource already exists" in error_info.error_msg:
                LOGGER.info(
                    "Resource already exists for revocation list: %s, "
                    "attempting to fetch existing resource",
                    payload.rev_reg_def_id,
                )

                try:
                    # Get the existing revocation list from the registry
                    anoncreds_registry = profile.inject(AnonCredsRegistry)
                    get_rev_list_result: GetRevListResult = (
                        await anoncreds_registry.get_revocation_list(
                            profile=profile,
                            rev_reg_def_id=payload.rev_reg_def_id,
                        )
                    )

                    # Convert GetRevListResult to RevListResult for downstream processing
                    rev_list_state = RevListState(
                        state=STATE_FINISHED,  # Assume existing rev list is finished
                        revocation_list=get_rev_list_result.revocation_list,
                    )

                    rev_list_result = RevListResult(
                        job_id=None,  # No job_id for existing resource
                        revocation_list_state=rev_list_state,
                        registration_metadata={},
                        revocation_list_metadata={},
                    )

                    LOGGER.info(
                        "Successfully recovered existing revocation list for: %s",
                        payload.rev_reg_def_id,
                    )

                    # Mark the event as completed since we recovered
                    if correlation_id:
                        async with profile.session() as session:
                            event_storage = EventStorageManager(session)
                            await event_storage.update_event_response(
                                event_type=RECORD_TYPE_REV_LIST_CREATE_EVENT,
                                correlation_id=correlation_id,
                                success=True,
                                response_data=serialize_event_payload(payload),
                            )
                            await event_storage.mark_event_completed(
                                event_type=RECORD_TYPE_REV_LIST_CREATE_EVENT,
                                correlation_id=correlation_id,
                            )

                    # Emit store request event with recovered result
                    revoc = AnonCredsRevocation(profile)
                    await revoc.emit_store_revocation_list_event(
                        rev_reg_def_id=payload.rev_reg_def_id,
                        result=rev_list_result,
                        options=self._clean_options_for_new_request(payload.options),
                    )
                    return  # Successfully recovered, exit early

                except Exception as recovery_err:
                    LOGGER.error(
                        "Failed to recover existing revocation list for: %s, error: %s",
                        payload.rev_reg_def_id,
                        str(recovery_err),
                    )
                    # Fall through to retry logic or mark as failed

            # Implement retry logic
            if error_info.should_retry and error_info.retry_count < self.MAX_RETRY_COUNT:
                LOGGER.info(
                    "Retrying revocation list creation, attempt %d",
                    error_info.retry_count + 1,
                )

                new_options = payload.options.copy()
                new_options["retry_count"] = error_info.retry_count + 1

                revoc = AnonCredsRevocation(profile)
                await revoc.emit_create_and_register_revocation_list_event(
                    payload.rev_reg_def_id, new_options
                )
            else:
                LOGGER.error(
                    "Max retries exceeded for revocation list creation: %s",
                    payload.rev_reg_def_id,
                )
                # Mark the event as completed since we won't retry
                if correlation_id:
                    async with profile.session() as session:
                        event_storage = EventStorageManager(session)
                        await event_storage.mark_event_completed(
                            event_type=RECORD_TYPE_REV_LIST_CREATE_EVENT,
                            correlation_id=correlation_id,
                        )
                # TODO: Implement notification to issuer about failure
        else:
            # Handle success
            LOGGER.info(
                "Revocation list creation succeeded for: %s", payload.rev_reg_def_id
            )

            # Emit store request event
            revoc = AnonCredsRevocation(profile)
            await revoc.emit_store_revocation_list_event(
                rev_reg_def_id=payload.rev_reg_def_id,
                result=payload.rev_list_result,
                options=self._clean_options_for_new_request(payload.options),
            )

    async def on_rev_list_finished(
        self, profile: Profile, event: RevListFinishedEvent
    ) -> None:
        """Handle rev list finished."""
        await notify_revocation_published_event(
            profile, event.payload.rev_reg_id, event.payload.revoked
        )

    async def on_rev_list_store_requested(
        self, profile: Profile, event: RevListStoreRequestedEvent
    ) -> None:
        """Handle revocation list store request."""
        payload = event.payload
        revoc = AnonCredsRevocation(profile)

        # Check if this is a retry with existing correlation_id
        correlation_id = payload.options.get("correlation_id")
        if not correlation_id:
            # Generate new correlation_id for new requests
            correlation_id = generate_correlation_id()

            # Persist the request event only for new requests
            async with profile.session() as session:
                event_storage = EventStorageManager(session)
                await event_storage.store_event_request(
                    event_type=RECORD_TYPE_REV_LIST_STORE_EVENT,
                    event_data=serialize_event_payload(payload),
                    correlation_id=correlation_id,
                    options=payload.options,
                )

        LOGGER.debug(
            "Handling revocation list store request for: %s, correlation_id: %s",
            payload.rev_reg_def_id,
            correlation_id,
        )

        # Store correlation_id in options for response tracking
        options_with_correlation = payload.options.copy()
        options_with_correlation["correlation_id"] = correlation_id

        await revoc.handle_store_revocation_list_request(
            rev_reg_def_id=payload.rev_reg_def_id,
            result=payload.result,
            options=options_with_correlation,
        )

    async def on_rev_list_store_response(
        self, profile: Profile, event: RevListStoreResponseEvent
    ) -> None:
        """Handle revocation list store response."""
        payload = event.payload

        # Update the persisted event with response information
        correlation_id = payload.options.get("correlation_id")
        if correlation_id:
            async with profile.session() as session:
                event_storage = EventStorageManager(session)
                if payload.failure:
                    await event_storage.update_event_response(
                        event_type=RECORD_TYPE_REV_LIST_STORE_EVENT,
                        correlation_id=correlation_id,
                        success=False,
                        response_data=serialize_event_payload(payload),
                        error_msg=payload.failure.error_info.error_msg,
                    )
                else:
                    await event_storage.update_event_response(
                        event_type=RECORD_TYPE_REV_LIST_STORE_EVENT,
                        correlation_id=correlation_id,
                        success=True,
                        response_data=serialize_event_payload(payload),
                    )
        else:
            LOGGER.warning("No correlation_id found for rev list store response")

        if payload.failure:
            # Handle failure
            failure = payload.failure
            error_info = failure.error_info

            LOGGER.error(
                "Revocation list store failed for: %s, error: %s",
                payload.rev_reg_def_id,
                error_info.error_msg,
            )

            # Implement retry logic
            if error_info.should_retry and error_info.retry_count < self.MAX_RETRY_COUNT:
                LOGGER.info(
                    "Retrying revocation list store, attempt %d",
                    error_info.retry_count + 1,
                )

                new_options = payload.options.copy()
                new_options["retry_count"] = error_info.retry_count + 1

                revoc = AnonCredsRevocation(profile)
                await revoc.handle_store_revocation_list_request(
                    rev_reg_def_id=payload.rev_reg_def_id,
                    result=failure.result,
                    options=new_options,
                )
            else:
                LOGGER.error(
                    "Max retries exceeded for revocation list store: %s",
                    payload.rev_reg_def_id,
                )
                # Mark the event as completed since we won't retry
                if correlation_id:
                    async with profile.session() as session:
                        event_storage = EventStorageManager(session)
                        await event_storage.mark_event_completed(
                            event_type=RECORD_TYPE_REV_LIST_STORE_EVENT,
                            correlation_id=correlation_id,
                        )
                # TODO: Implement notification to issuer about failure
        else:
            # Handle success
            LOGGER.info("Revocation list store succeeded for: %s", payload.rev_reg_def_id)

            # Mark the event as completed on success
            if correlation_id:
                async with profile.session() as session:
                    event_storage = EventStorageManager(session)
                    await event_storage.mark_event_completed(
                        event_type=RECORD_TYPE_REV_LIST_STORE_EVENT,
                        correlation_id=correlation_id,
                    )

            # If this is for the first registry, activate it
            revoc = AnonCredsRevocation(profile)
            options = self._clean_options_for_new_request(payload.options)
            first_registry = options.pop("first_registry", False)
            if first_registry:
                await revoc.emit_set_active_registry_event(
                    rev_reg_def_id=payload.rev_reg_def_id,
                    options=options,
                )

    async def on_registry_activation_requested(
        self, profile: Profile, event: RevRegActivationRequestedEvent
    ) -> None:
        """Handle registry activation request."""
        payload = event.payload
        revoc = AnonCredsRevocation(profile)

        # Check if this is a retry with existing correlation_id
        correlation_id = payload.options.get("correlation_id")
        if not correlation_id:
            # Generate new correlation_id for new requests
            correlation_id = generate_correlation_id()

            # Persist the request event only for new requests
            async with profile.session() as session:
                event_storage = EventStorageManager(session)
                await event_storage.store_event_request(
                    event_type=RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
                    event_data=serialize_event_payload(payload),
                    correlation_id=correlation_id,
                    options=payload.options,
                )

        LOGGER.debug(
            "Handling registry activation request for: %s, correlation_id: %s",
            payload.rev_reg_def_id,
            correlation_id,
        )

        # Store correlation_id in options for response tracking
        options_with_correlation = payload.options.copy()
        options_with_correlation["correlation_id"] = correlation_id

        await revoc.handle_activate_registry_request(
            rev_reg_def_id=payload.rev_reg_def_id,
            options=options_with_correlation,
        )

    async def on_registry_activation_response(
        self, profile: Profile, event: RevRegActivationResponseEvent
    ) -> None:
        """Handle registry activation response."""
        payload = event.payload

        # Update the persisted event with response information
        correlation_id = payload.options.get("correlation_id")
        if correlation_id:
            async with profile.session() as session:
                event_storage = EventStorageManager(session)
                if payload.failure:
                    await event_storage.update_event_response(
                        event_type=RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
                        correlation_id=correlation_id,
                        success=False,
                        response_data=serialize_event_payload(payload),
                        error_msg=payload.failure.error_info.error_msg,
                    )
                else:
                    await event_storage.update_event_response(
                        event_type=RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
                        correlation_id=correlation_id,
                        success=True,
                        response_data=serialize_event_payload(payload),
                    )
        else:
            LOGGER.warning("No correlation_id found for rev reg def activation response")

        if payload.failure:
            # Handle failure
            failure = payload.failure
            error_info = failure.error_info

            LOGGER.error(
                "Registry activation failed for: %s, error: %s",
                payload.rev_reg_def_id,
                error_info.error_msg,
            )

            # Implement retry logic
            if error_info.retry_count < self.MAX_RETRY_COUNT:
                LOGGER.info(
                    "Retrying registry activation, attempt %d", error_info.retry_count + 1
                )

                new_options = payload.options.copy()
                new_options["retry_count"] = error_info.retry_count + 1

                revoc = AnonCredsRevocation(profile)
                await revoc.emit_set_active_registry_event(
                    payload.rev_reg_def_id, new_options
                )
            else:
                LOGGER.error(
                    "Max retries exceeded for registry activation: %s",
                    payload.rev_reg_def_id,
                )
                # Mark the event as completed since we won't retry
                if correlation_id:
                    async with profile.session() as session:
                        event_storage = EventStorageManager(session)
                        await event_storage.mark_event_completed(
                            event_type=RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
                            correlation_id=correlation_id,
                        )
                # TODO: Implement notification to issuer about failure
        else:
            # Handle success
            LOGGER.info("Registry activation succeeded for: %s", payload.rev_reg_def_id)

            # Mark the event as completed on success
            if correlation_id:
                async with profile.session() as session:
                    event_storage = EventStorageManager(session)
                    await event_storage.mark_event_completed(
                        event_type=RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
                        correlation_id=correlation_id,
                    )

            # Check if this request was part of full registry handling; then create backup
            if payload.options.get("cred_def_id") and payload.options.get(
                "old_rev_reg_def_id"
            ):
                # Get the registry definition to extract issuer details
                revoc = AnonCredsRevocation(profile)
                rev_reg_def = await revoc.get_created_revocation_registry_definition(
                    payload.rev_reg_def_id
                )

                if rev_reg_def:
                    # Create new backup registry
                    LOGGER.debug(
                        "Emitting event to create new backup registry for cred def id %s",
                        payload.options["cred_def_id"],
                    )
                    await revoc.emit_create_revocation_registry_definition_event(
                        issuer_id=rev_reg_def.issuer_id,
                        cred_def_id=payload.options["cred_def_id"],
                        registry_type=rev_reg_def.type,
                        tag=revoc._generate_backup_registry_tag(),
                        max_cred_num=rev_reg_def.value.max_cred_num,
                        options=self._clean_options_for_new_request(payload.options),
                    )
                else:
                    LOGGER.error(
                        "Could not retrieve registry definition %s for creating backup",
                        payload.rev_reg_def_id,
                    )

    async def on_registry_full_detected(
        self, profile: Profile, event: RevRegFullDetectedEvent
    ) -> None:
        """Handle registry full detection."""
        payload = event.payload
        revoc = AnonCredsRevocation(profile)

        # Check if this is a retry with existing correlation_id
        correlation_id = payload.options.get("correlation_id")
        if not correlation_id:
            # Generate new correlation_id for new requests
            correlation_id = generate_correlation_id()

            # Persist the request event only for new requests
            async with profile.session() as session:
                event_storage = EventStorageManager(session)
                await event_storage.store_event_request(
                    event_type=RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
                    event_data=serialize_event_payload(payload),
                    correlation_id=correlation_id,
                    options=payload.options,
                )

        LOGGER.info(
            "Full registry detected: %s, correlation_id: %s",
            payload.rev_reg_def_id,
            correlation_id,
        )

        # Store correlation_id in options for response tracking
        options_with_correlation = payload.options.copy()
        options_with_correlation["correlation_id"] = correlation_id

        # Start the full registry handling process
        await revoc.handle_full_registry_event(
            rev_reg_def_id=payload.rev_reg_def_id,
            cred_def_id=payload.cred_def_id,
            options=options_with_correlation,
        )

    async def on_registry_full_handling_response(
        self, profile: Profile, event: RevRegFullHandlingResponseEvent
    ) -> None:
        """Handle registry full handling completed."""
        payload = event.payload

        # Update the persisted event with response information
        correlation_id = payload.options.get("correlation_id")
        if correlation_id:
            async with profile.session() as session:
                event_storage = EventStorageManager(session)
                if payload.failure:
                    await event_storage.update_event_response(
                        event_type=RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
                        correlation_id=correlation_id,
                        success=False,
                        response_data=serialize_event_payload(payload),
                        error_msg=payload.failure.error_info.error_msg,
                    )
                else:
                    await event_storage.update_event_response(
                        event_type=RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
                        correlation_id=correlation_id,
                        success=True,
                        response_data=serialize_event_payload(payload),
                    )
        else:
            LOGGER.warning("No correlation_id found for full registry handling response")

        if payload.failure:
            failure = payload.failure
            error_info = failure.error_info

            LOGGER.error(
                "Full registry handling failed for: %s, error: %s",
                payload.old_rev_reg_def_id,
                error_info.error_msg,
            )

            # Implement retry logic
            if error_info.retry_count < self.MAX_RETRY_COUNT:
                LOGGER.info(
                    "Retrying full registry handling, attempt %d",
                    error_info.retry_count + 1,
                )

                new_options = payload.options.copy()
                new_options["retry_count"] = error_info.retry_count + 1

                revoc = AnonCredsRevocation(profile)
                await revoc.handle_full_registry_event(
                    rev_reg_def_id=payload.old_rev_reg_def_id,
                    cred_def_id=payload.cred_def_id,
                    options=new_options,
                )
            else:
                LOGGER.error(
                    "Max retries exceeded for full registry handling: %s",
                    payload.old_rev_reg_def_id,
                )
                # Mark the event as completed since we won't retry
                if correlation_id:
                    async with profile.session() as session:
                        event_storage = EventStorageManager(session)
                        await event_storage.mark_event_completed(
                            event_type=RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
                            correlation_id=correlation_id,
                        )
                # TODO: Implement notification to issuer about failure

        else:
            LOGGER.info(
                "Full registry handling response. Old: %s, New Active: %s",
                payload.old_rev_reg_def_id,
                payload.new_active_rev_reg_def_id,
            )

            # Mark the event as completed on success
            if correlation_id:
                async with profile.session() as session:
                    event_storage = EventStorageManager(session)
                    await event_storage.mark_event_completed(
                        event_type=RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
                        correlation_id=correlation_id,
                    )

    # Helper methods for error handling and notifications
    async def _notify_issuer_about_failure(
        self,
        profile: Profile,
        failure_type: str,
        identifier: str,
        error_msg: str,
        options: dict,
    ) -> None:
        """Notify issuer about a failure that couldn't be automatically recovered.

        Args:
            profile (Profile): The profile context
            failure_type (str): Type of failure (e.g. "registry_creation", "tails_upload")
            identifier (str): Identifier for the failed operation
            error_msg (str): Error message
            options (dict): Options context

        """
        # This is a placeholder for future implementation
        # In a real implementation, this could:
        # 1. Send webhook notifications
        # 2. Log to a persistent failure tracking system
        # 3. Send admin notifications
        # 4. Create manual intervention tasks

        LOGGER.critical(
            f"MANUAL INTERVENTION REQUIRED: {failure_type} failed for {identifier} "
            f"after maximum retries. Error: {error_msg}"
        )

        # TODO: Implement actual notification mechanisms:
        # - Webhook notifications to issuer
        # - Admin dashboard alerts
        # - Email notifications
        # - Persistent failure tracking
