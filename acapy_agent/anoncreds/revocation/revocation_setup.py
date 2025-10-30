"""Automated setup process for AnonCreds credential definitions with revocation."""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from ...core.event_bus import Event, EventBus
from ...core.profile import Profile
from ...revocation.util import notify_revocation_published_event
from ...storage.type import (
    RECORD_TYPE_REV_LIST_CREATE_EVENT,
    RECORD_TYPE_REV_LIST_STORE_EVENT,
    RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
    RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
    RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
    RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
)
from ..events import (
    FIRST_REGISTRY_TAG,
    INTERVENTION_REQUIRED_EVENT,
    BaseEventPayload,
    BasePayloadWithFailure,
    CredDefFinishedEvent,
    InterventionRequiredPayload,
    RevListCreateRequestedEvent,
    RevListCreateResponseEvent,
    RevListFinishedEvent,
    RevListStoreRequestedEvent,
    RevListStoreResponseEvent,
    RevRegActivationRequestedEvent,
    RevRegActivationResponseEvent,
    RevRegDefCreateRequestedEvent,
    RevRegDefCreateResponseEvent,
    RevRegDefStoreRequestedEvent,
    RevRegDefStoreResponseEvent,
    RevRegFullDetectedEvent,
    RevRegFullHandlingResponseEvent,
)
from ..issuer import STATE_FINISHED
from ..revocation import AnonCredsRevocation
from .auto_recovery import (
    EventStorageManager,
    calculate_event_expiry_timestamp,
    calculate_exponential_backoff_delay,
    generate_correlation_id,
    generate_request_id,
    serialize_event_payload,
)

LOGGER = logging.getLogger(__name__)


class AnonCredsRevocationSetupManager(ABC):
    """Base class for automated setup of revocation."""

    @abstractmethod
    def register_events(self, event_bus: EventBus) -> None:
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

    def __init__(self) -> None:
        """Init manager."""

    async def _setup_request_correlation(
        self,
        profile: Profile,
        payload: BaseEventPayload,
        event_type: str,
    ) -> tuple[str, dict]:
        """Set up correlation ID and event storage for request handlers.

        Args:
            profile: The profile context
            payload: The event payload containing options
            event_type: The event type for storage

        Returns:
            tuple: (correlation_id, options_with_correlation)

        """
        # Check if this is a retry with existing correlation_id
        correlation_id = payload.options.get("correlation_id")
        if not correlation_id:
            # Generate new correlation_id for new requests
            correlation_id = generate_correlation_id()

            # Persist the request event only for new requests
            async with profile.session() as session:
                event_storage = EventStorageManager(session)

                # Calculate expiry timestamp based on current retry count
                retry_count = payload.options.get("retry_count", 0)
                expiry_timestamp = calculate_event_expiry_timestamp(retry_count)

                await event_storage.store_event_request(
                    event_type=event_type,
                    event_data=serialize_event_payload(payload),
                    correlation_id=correlation_id,
                    request_id=payload.options.get("request_id"),
                    options=payload.options,
                    expiry_timestamp=expiry_timestamp,
                )

        # Store correlation_id in options for response tracking
        options_with_correlation = payload.options.copy()
        options_with_correlation["correlation_id"] = correlation_id

        return correlation_id, options_with_correlation

    async def _handle_response_failure(
        self,
        profile: Profile,
        payload: BasePayloadWithFailure,
        event_type: str,
        correlation_id: str,
        failure_type: str,
        retry_callback: Callable[..., Awaitable[Any]],
    ) -> bool:
        """Handle failure response with retry logic.

        Args:
            profile: The profile context
            payload: The event payload containing failure info
            event_type: The event type for storage
            correlation_id: The correlation ID for tracking
            failure_type: Description of the failure type for logging
            retry_callback: Function to call for retry

        Returns:
            bool: True if retry was attempted, False if not retryable

        """
        failure = payload.failure
        error_info = failure.error_info

        # Log error details based on available failure attributes
        identifier: str = (
            getattr(failure, "cred_def_id", None)  # type: ignore[assignment]
            or getattr(failure, "rev_reg_def_id", None)
            or getattr(payload, "rev_reg_def_id", "unknown")
        )

        LOGGER.warning(
            "%s failed for %s, request_id: %s, correlation_id: %s, error: %s",
            failure_type.replace("_", " ").title(),
            identifier,
            payload.options.get("request_id"),
            correlation_id,
            error_info.error_msg,
        )

        # Implement exponential backoff retry logic
        if error_info.should_retry:
            retry_delay = calculate_exponential_backoff_delay(error_info.retry_count)

            LOGGER.info(
                "Retrying %s for %s, request_id: %s, correlation_id: %s. "
                "Attempt %d, delay %d seconds",
                failure_type.replace("_", " "),
                identifier,
                payload.options.get("request_id"),
                correlation_id,
                error_info.retry_count + 1,
                retry_delay,
            )

            await asyncio.sleep(retry_delay)

            # Update options with new retry count and update event for retry
            new_options = payload.options.copy()
            new_options["retry_count"] = error_info.retry_count + 1

            if correlation_id:
                async with profile.session() as session:
                    event_storage = EventStorageManager(session)
                    # Update the event for retry (sets state to REQUESTED)
                    await event_storage.update_event_for_retry(
                        event_type=event_type,
                        correlation_id=correlation_id,
                        error_msg=error_info.error_msg,
                        retry_count=error_info.retry_count + 1,
                        updated_options=new_options,
                    )

            # Execute retry callback
            await retry_callback(options=new_options)
            return True
        else:
            # Not retryable, update event as failed and notify issuer
            LOGGER.error(
                "Won't retry %s for %s, request_id: %s, correlation_id: %s",
                failure_type.replace("_", " "),
                identifier,
                payload.options.get("request_id"),
                correlation_id,
            )

            # Update event as failed and mark as completed
            if correlation_id:
                async with profile.session() as session:
                    event_storage = EventStorageManager(session)
                    await event_storage.update_event_response(
                        event_type=event_type,
                        correlation_id=correlation_id,
                        success=False,
                        response_data=serialize_event_payload(payload),
                        error_msg=error_info.error_msg,
                    )

            await self._notify_issuer_about_failure(
                profile=profile,
                failure_type=failure_type,
                identifier=identifier,
                error_msg=error_info.error_msg,
                options=payload.options,
            )
            return False

    async def _handle_response_success(
        self,
        profile: Profile,
        payload: BaseEventPayload,
        event_type: str,
        correlation_id: str,
        success_message: str,
    ) -> None:
        """Handle success response by updating event storage.

        Args:
            profile: The profile context
            payload: The event payload
            event_type: The event type for storage
            correlation_id: The correlation ID for tracking
            success_message: Log message for success

        """
        # Log success
        LOGGER.info(success_message)

        # Update event as successful and mark as completed
        if correlation_id:
            async with profile.session() as session:
                event_storage = EventStorageManager(session)
                await event_storage.update_event_response(
                    event_type=event_type,
                    correlation_id=correlation_id,
                    success=True,
                    response_data=serialize_event_payload(payload),
                )

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

            # Generate a new request_id for this revocation registry workflow
            request_id = generate_request_id()
            options = self._clean_options_for_new_request(payload.options)
            options["request_id"] = request_id

            LOGGER.info(
                "Starting revocation registry workflow for cred_def_id: %s, "
                "request_id: %s",
                payload.cred_def_id,
                request_id,
            )

            # Emit event to request creation and registration of a revocation registry
            # This automates the creation of a backup registry and accompanying resources
            await revoc.emit_create_revocation_registry_definition_event(
                issuer_id=payload.issuer_id,
                cred_def_id=payload.cred_def_id,
                registry_type=self.REGISTRY_TYPE,
                max_cred_num=payload.max_cred_num,
                tag=FIRST_REGISTRY_TAG,
                options=options,
            )

            if event.payload.options.get("wait_for_revocation_setup"):
                # Wait for registry activation, if configured to do so
                await revoc.wait_for_active_revocation_registry(payload.cred_def_id)

    async def on_registry_create_requested(
        self, profile: Profile, event: RevRegDefCreateRequestedEvent
    ) -> None:
        """Handle registry creation request."""
        payload = event.payload
        revoc = AnonCredsRevocation(profile)

        correlation_id, options_with_correlation = await self._setup_request_correlation(
            profile,
            payload,  # type: ignore[arg-type]
            RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
        )

        LOGGER.debug(
            "Handling registry creation request for cred_def_id: %s, tag: %s, "
            "request_id: %s, correlation_id: %s",
            payload.cred_def_id,
            payload.tag,
            payload.options.get("request_id"),
            correlation_id,
        )

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
        correlation_id: str = payload.options.get("correlation_id", "")

        if not correlation_id:  # pragma: no cover
            LOGGER.warning("No correlation_id found for rev reg def create response")

        if failure := payload.failure:
            # Define retry callback for registry creation
            async def retry_registry_creation(options):  # pragma: no cover
                revoc = AnonCredsRevocation(profile)
                await revoc.emit_create_revocation_registry_definition_event(
                    issuer_id=failure.issuer_id,
                    cred_def_id=failure.cred_def_id,
                    registry_type=failure.registry_type,
                    tag=failure.tag,
                    max_cred_num=failure.max_cred_num,
                    options=options,
                )

            await self._handle_response_failure(
                profile=profile,
                payload=payload,  # type: ignore[arg-type]
                event_type=RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
                correlation_id=correlation_id,
                failure_type="registry_create",
                retry_callback=retry_registry_creation,
            )
        else:
            if not payload.rev_reg_def_result or not payload.rev_reg_def:
                #  For type checks; should never happen
                LOGGER.error("Expected rev_reg_def to be present in successful response")
                return

            # Handle success
            success_message = (
                f"Registry creation succeeded for "
                f"rev_reg_def_id: {payload.rev_reg_def_result.rev_reg_def_id}, "
                f"request_id: {payload.options.get('request_id')}, "
                f"correlation_id: {correlation_id}"
            )

            await self._handle_response_success(
                profile=profile,
                payload=payload,  # type: ignore[arg-type]
                event_type=RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
                correlation_id=correlation_id,
                success_message=success_message,
            )

            # Emit next event in chain - store request event
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

        _, options_with_correlation = await self._setup_request_correlation(
            profile,
            payload,  # type: ignore[arg-type]
            RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
        )

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
        correlation_id: str = payload.options.get("correlation_id", "")
        if not correlation_id:  # pragma: no cover
            LOGGER.warning("No correlation_id found for rev reg def store response")

        if payload.failure:
            # Define retry callback for registry store
            async def retry_registry_store(options):  # pragma: no cover
                revoc = AnonCredsRevocation(profile)
                await revoc.handle_store_revocation_registry_definition_request(
                    rev_reg_def_result=payload.rev_reg_def_result,
                    options=options,
                )

            await self._handle_response_failure(
                profile=profile,
                payload=payload,  # type: ignore[arg-type]
                event_type=RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
                correlation_id=correlation_id,
                failure_type="registry_store",
                retry_callback=retry_registry_store,
            )
        else:
            # Handle success
            success_message = (
                f"Registry store succeeded for rev_reg_def_id: {payload.rev_reg_def_id}, "
                f"tag: {payload.tag}, request_id: {payload.options.get('request_id')}, "
                f"correlation_id: {correlation_id}"
            )

            await self._handle_response_success(
                profile=profile,
                payload=payload,  # type: ignore[arg-type]
                event_type=RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
                correlation_id=correlation_id,
                success_message=success_message,
            )

            # Emit finished event
            revoc = AnonCredsRevocation(profile)
            state = payload.rev_reg_def_result.revocation_registry_definition_state.state
            if state == STATE_FINISHED:
                await revoc.emit_create_and_register_revocation_list_event(
                    rev_reg_def_id=payload.rev_reg_def_id,
                    options=self._clean_options_for_new_request(payload.options),
                )
            else:  # pragma: no cover
                LOGGER.warning(
                    "Revocation registry definition %s not finished; has state %s, "
                    "request_id: %s, correlation_id: %s",
                    payload.rev_reg_def_id,
                    state,
                    payload.options.get("request_id"),
                    payload.options.get("correlation_id"),
                )

            # If this is the first registry, trigger creation of backup registry
            if payload.tag == FIRST_REGISTRY_TAG:
                # Generate new request_id for backup registry workflow
                backup_request_id = generate_request_id()
                backup_options = self._clean_options_for_new_request(payload.options)
                backup_options["request_id"] = backup_request_id

                LOGGER.info(
                    "First registry stored successfully, "
                    "requesting creation of backup registry for cred_def_id: %s, "
                    "original request_id: %s, new backup request_id: %s",
                    payload.rev_reg_def.cred_def_id,
                    payload.options.get("request_id"),
                    backup_request_id,
                )

                await revoc.emit_create_revocation_registry_definition_event(
                    issuer_id=payload.rev_reg_def.issuer_id,
                    cred_def_id=payload.rev_reg_def.cred_def_id,
                    registry_type=payload.rev_reg_def.type,
                    tag=revoc._generate_backup_registry_tag(),
                    max_cred_num=payload.rev_reg_def.value.max_cred_num,
                    options=backup_options,
                )

    async def on_rev_list_create_requested(
        self, profile: Profile, event: RevListCreateRequestedEvent
    ) -> None:
        """Handle revocation list creation request."""
        payload = event.payload
        revoc = AnonCredsRevocation(profile)

        correlation_id, options_with_correlation = await self._setup_request_correlation(
            profile,
            payload,  # type: ignore[arg-type]
            RECORD_TYPE_REV_LIST_CREATE_EVENT,
        )

        LOGGER.debug(
            "Handling revocation list creation request for rev_reg_def_id: %s, "
            "request_id: %s, correlation_id: %s",
            payload.rev_reg_def_id,
            payload.options.get("request_id"),
            correlation_id,
        )

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
        correlation_id: str = payload.options.get("correlation_id", "")
        if not correlation_id:  # pragma: no cover
            LOGGER.warning("No correlation_id found for rev list create response")

        if payload.failure:
            # Define retry callback for rev list creation
            async def retry_rev_list_creation(options):  # pragma: no cover
                revoc = AnonCredsRevocation(profile)
                await revoc.emit_create_and_register_revocation_list_event(
                    payload.rev_reg_def_id, options
                )

            await self._handle_response_failure(
                profile=profile,
                payload=payload,  # type: ignore[arg-type]
                event_type=RECORD_TYPE_REV_LIST_CREATE_EVENT,
                correlation_id=correlation_id,
                failure_type="rev_list_create",
                retry_callback=retry_rev_list_creation,
            )
        else:
            if not payload.rev_list_result:
                #  For type checks; should never happen
                LOGGER.error(
                    "Expected rev_list_result to exist in successful create response"
                )
                return

            # Handle success
            success_message = (
                f"Revocation list creation succeeded for "
                f"rev_reg_def_id: {payload.rev_reg_def_id}, "
                f"request_id: {payload.options.get('request_id')}, "
                f"correlation_id: {correlation_id}"
            )

            await self._handle_response_success(
                profile=profile,
                payload=payload,  # type: ignore[arg-type]
                event_type=RECORD_TYPE_REV_LIST_CREATE_EVENT,
                correlation_id=correlation_id,
                success_message=success_message,
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

        correlation_id, options_with_correlation = await self._setup_request_correlation(
            profile,
            payload,  # type: ignore[arg-type]
            RECORD_TYPE_REV_LIST_STORE_EVENT,
        )

        LOGGER.debug(
            "Handling revocation list store request for rev_reg_def_id: %s, "
            "request_id: %s, correlation_id: %s",
            payload.rev_reg_def_id,
            payload.options.get("request_id"),
            correlation_id,
        )

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
        correlation_id: str = payload.options.get("correlation_id", "")
        if not correlation_id:  # pragma: no cover
            LOGGER.warning("No correlation_id found for rev list store response")

        if payload.failure:
            # Define retry callback for rev list store
            async def retry_rev_list_store(options):  # pragma: no cover
                revoc = AnonCredsRevocation(profile)
                await revoc.handle_store_revocation_list_request(
                    rev_reg_def_id=payload.rev_reg_def_id,
                    result=payload.result,
                    options=options,
                )

            await self._handle_response_failure(
                profile=profile,
                payload=payload,  # type: ignore[arg-type]
                event_type=RECORD_TYPE_REV_LIST_STORE_EVENT,
                correlation_id=correlation_id,
                failure_type="rev_list_store",
                retry_callback=retry_rev_list_store,
            )
        else:
            # Handle success
            success_message = (
                f"Revocation list store succeeded for "
                f"rev_reg_def_id: {payload.rev_reg_def_id}, "
                f"request_id: {payload.options.get('request_id')}, "
                f"correlation_id: {correlation_id}"
            )

            await self._handle_response_success(
                profile=profile,
                payload=payload,  # type: ignore[arg-type]
                event_type=RECORD_TYPE_REV_LIST_STORE_EVENT,
                correlation_id=correlation_id,
                success_message=success_message,
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

        correlation_id, options_with_correlation = await self._setup_request_correlation(
            profile,
            payload,  # type: ignore[arg-type]
            RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
        )

        LOGGER.debug(
            "Handling registry activation request for rev_reg_def_id: %s, "
            "cred_def_id: %s, request_id: %s, correlation_id: %s",
            payload.rev_reg_def_id,
            payload.options.get("cred_def_id"),
            payload.options.get("request_id"),
            correlation_id,
        )

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
        correlation_id: str = payload.options.get("correlation_id", "")
        if not correlation_id:  # pragma: no cover
            LOGGER.warning("No correlation_id found for rev reg def activation response")

        if payload.failure:

            async def retry_activation(options):  # pragma: no cover
                revoc = AnonCredsRevocation(profile)
                await revoc.emit_set_active_registry_event(
                    payload.rev_reg_def_id, options
                )

            await self._handle_response_failure(
                profile=profile,
                payload=payload,  # type: ignore[arg-type]
                event_type=RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
                correlation_id=correlation_id,
                failure_type="registry_activation",
                retry_callback=retry_activation,
            )
        else:
            # Handle success
            LOGGER.info(
                "Registry activation succeeded for rev_reg_def_id: %s, "
                "cred_def_id: %s, request_id: %s, correlation_id: %s",
                payload.rev_reg_def_id,
                payload.options.get("cred_def_id"),
                payload.options.get("request_id"),
                payload.options.get("correlation_id"),
            )

            # Update event as successful and mark as completed
            if correlation_id:
                async with profile.session() as session:
                    event_storage = EventStorageManager(session)
                    await event_storage.update_event_response(
                        event_type=RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
                        correlation_id=correlation_id,
                        success=True,
                        response_data=serialize_event_payload(payload),
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
                    # Create new backup registry with same request_id
                    backup_options = self._clean_options_for_new_request(payload.options)
                    backup_options["request_id"] = payload.options.get("request_id")

                    LOGGER.debug(
                        "Emitting event to create new backup registry for "
                        "cred def id %s, request_id: %s, correlation_id: %s",
                        payload.options["cred_def_id"],
                        payload.options.get("request_id"),
                        payload.options.get("correlation_id"),
                    )
                    await revoc.emit_create_revocation_registry_definition_event(
                        issuer_id=rev_reg_def.issuer_id,
                        cred_def_id=payload.options["cred_def_id"],
                        registry_type=rev_reg_def.type,
                        tag=revoc._generate_backup_registry_tag(),
                        max_cred_num=rev_reg_def.value.max_cred_num,
                        options=backup_options,
                    )
                else:
                    LOGGER.error(
                        "Could not retrieve registry definition %s for creating backup",
                        payload.rev_reg_def_id,
                    )
                    await self._notify_issuer_about_failure(
                        profile=profile,
                        failure_type="registry_activation",
                        identifier=payload.rev_reg_def_id,
                        error_msg="Could not retrieve registry definition for creating backup",  # noqa: E501
                        options=payload.options,
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
            # Generate new correlation_id and request_id for new full registry handling
            correlation_id = generate_correlation_id()

            # Generate new request_id for full registry handling workflow
            if "request_id" not in payload.options:
                full_handling_request_id = generate_request_id()
                payload.options["request_id"] = full_handling_request_id

                LOGGER.info(
                    "Starting full registry handling workflow for rev_reg_def_id: %s, "
                    "cred_def_id: %s, request_id: %s",
                    payload.rev_reg_def_id,
                    payload.cred_def_id,
                    full_handling_request_id,
                )

            # Persist the request event only for new requests
            async with profile.session() as session:
                event_storage = EventStorageManager(session)

                # Calculate expiry timestamp based on current retry count
                retry_count = payload.options.get("retry_count", 0)
                expiry_timestamp = calculate_event_expiry_timestamp(retry_count)

                await event_storage.store_event_request(
                    event_type=RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
                    event_data=serialize_event_payload(payload),
                    correlation_id=correlation_id,
                    request_id=payload.options.get("request_id"),
                    options=payload.options,
                    expiry_timestamp=expiry_timestamp,
                )

        LOGGER.info(
            "Full registry detected for cred_def_id: %s. Full rev_reg_def_id: %s. "
            "request_id: %s. correlation_id: %s",
            payload.cred_def_id,
            payload.rev_reg_def_id,
            payload.options.get("request_id"),
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
        correlation_id: str = payload.options.get("correlation_id", "")
        if not correlation_id:  # pragma: no cover
            LOGGER.warning("No correlation_id found for full registry handling response")

        if payload.failure:
            # Define retry callback for full registry handling
            async def retry_full_registry_handling(options):  # pragma: no cover
                revoc = AnonCredsRevocation(profile)
                await revoc.handle_full_registry_event(
                    rev_reg_def_id=payload.old_rev_reg_def_id,
                    cred_def_id=payload.cred_def_id,
                    options=options,
                )

            await self._handle_response_failure(
                profile=profile,
                payload=payload,  # type: ignore[arg-type]
                event_type=RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
                correlation_id=correlation_id,
                failure_type="full_registry_handling",
                retry_callback=retry_full_registry_handling,
            )

        else:
            # Handle success
            success_message = (
                f"Full registry handling response. "
                f"Old rev reg def id: {payload.old_rev_reg_def_id}, "
                f"new active rev reg def id: {payload.new_active_rev_reg_def_id}, "
                f"cred_def_id: {payload.cred_def_id}, "
                f"request_id: {payload.options.get('request_id')}, "
                f"correlation_id: {correlation_id}"
            )

            await self._handle_response_success(
                profile=profile,
                payload=payload,  # type: ignore[arg-type]
                event_type=RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
                correlation_id=correlation_id,
                success_message=success_message,
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
        LOGGER.error(
            f"MANUAL INTERVENTION REQUIRED: {failure_type} failed for {identifier} "
            f"after maximum retries. Error: {error_msg}. Options: {options}"
        )

        event_bus = profile.inject_or(EventBus)
        if event_bus:
            await event_bus.notify(
                profile=profile,
                event=Event(
                    topic=INTERVENTION_REQUIRED_EVENT,
                    payload=InterventionRequiredPayload(
                        point_of_failure=failure_type,
                        error_msg=error_msg,
                        identifier=identifier,
                        options=options,
                    ),
                ),
            )
        else:
            LOGGER.error(
                "Could not notify issuer %s about failure %s for %s",
                profile.name,
                failure_type,
                identifier,
            )
