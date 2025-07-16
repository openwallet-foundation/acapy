"""Automated setup process for AnonCreds credential definitions with revocation."""

import logging
from abc import ABC, abstractmethod

from acapy_agent.anoncreds.issuer import STATE_FINISHED
from acapy_agent.protocols.endorse_transaction.v1_0.util import is_author_role

from ..anoncreds.revocation import AnonCredsRevocation, AnonCredsRevocationError
from ..core.event_bus import EventBus
from ..core.profile import Profile
from ..revocation.util import notify_revocation_published_event
from .events import (
    FIRST_REGISTRY_TAG,
    CredDefFinishedEvent,
    RevListFinishedEvent,
    RevRegDefFinishedEvent,
    RevRegDefCreateRequestedEvent,
    RevRegDefCreateResponseEvent,
    RevRegDefStoreRequestedEvent,
    RevRegDefStoreResponseEvent,
    TailsUploadRequestedEvent,
    TailsUploadResponseEvent,
    RevListCreateRequestedEvent,
    RevListCreateResponseEvent,
    RevListStoreRequestedEvent,
    RevListStoreResponseEvent,
    RevRegActivationRequestedEvent,
    RevRegActivationResponseEvent,
    RevRegFullDetectedEvent,
    RevRegFullHandlingStartedEvent,
    RevRegFullHandlingCompletedEvent,
    RevRegFullHandlingFailedEvent,
)

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

    def register_events(self, event_bus: EventBus) -> None:
        """Register event listeners."""
        # On cred def, request creation and registration of a revocation registry
        event_bus.subscribe(CredDefFinishedEvent.event_topic, self.on_cred_def)

        event_bus.subscribe(RevListFinishedEvent.event_topic, self.on_rev_list_finished)

        # On registry create requested, create and register a revocation registry
        event_bus.subscribe(
            RevRegDefCreateRequestedEvent.event_topic, self.on_registry_create_requested
        )
        # On registry create response, store the revocation registry
        event_bus.subscribe(
            RevRegDefCreateResponseEvent.event_topic, self.on_registry_create_response
        )

        event_bus.subscribe(
            RevRegDefStoreRequestedEvent.event_topic, self.on_registry_store_requested
        )
        event_bus.subscribe(
            RevRegDefStoreResponseEvent.event_topic, self.on_registry_store_response
        )

        event_bus.subscribe(RevRegDefFinishedEvent.event_topic, self.on_rev_reg_def)

        event_bus.subscribe(
            TailsUploadRequestedEvent.event_topic, self.on_tails_upload_requested
        )
        event_bus.subscribe(
            TailsUploadResponseEvent.event_topic, self.on_tails_upload_response
        )

        event_bus.subscribe(
            RevListCreateRequestedEvent.event_topic, self.on_rev_list_create_requested
        )
        event_bus.subscribe(
            RevListCreateResponseEvent.event_topic, self.on_rev_list_create_response
        )

        event_bus.subscribe(
            RevListStoreRequestedEvent.event_topic, self.on_rev_list_store_requested
        )
        event_bus.subscribe(
            RevListStoreResponseEvent.event_topic, self.on_rev_list_store_response
        )

        event_bus.subscribe(
            RevRegActivationRequestedEvent.event_topic,
            self.on_registry_activation_requested,
        )
        event_bus.subscribe(
            RevRegActivationResponseEvent.event_topic,
            self.on_registry_activation_response,
        )

        event_bus.subscribe(
            RevRegFullDetectedEvent.event_topic,
            self.on_registry_full_detected,
        )
        event_bus.subscribe(
            RevRegFullHandlingStartedEvent.event_topic,
            self.on_registry_full_handling_started,
        )
        event_bus.subscribe(
            RevRegFullHandlingCompletedEvent.event_topic,
            self.on_registry_full_handling_completed,
        )
        event_bus.subscribe(
            RevRegFullHandlingFailedEvent.event_topic,
            self.on_registry_full_handling_failed,
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
                options=payload.options,
            )

    async def on_registry_create_requested(  # ✅
        self, profile: Profile, event: RevRegDefCreateRequestedEvent
    ) -> None:
        """Handle registry creation request."""
        payload = event.payload
        revoc = AnonCredsRevocation(profile)

        LOGGER.debug(
            "Handling registry creation request for cred_def_id: %s, tag: %s",
            payload.cred_def_id,
            payload.tag,
        )

        await revoc.create_and_register_revocation_registry_definition(
            issuer_id=payload.issuer_id,
            cred_def_id=payload.cred_def_id,
            registry_type=payload.registry_type,
            tag=payload.tag,
            max_cred_num=payload.max_cred_num,
            options=payload.options,
        )

    async def on_registry_create_response(
        self, profile: Profile, event: RevRegDefCreateResponseEvent
    ) -> None:
        """Handle registry creation response."""
        payload = event.payload
        registry_type = "initial" if payload.tag == FIRST_REGISTRY_TAG else "backup"

        if payload.error_msg:
            # Handle failure
            LOGGER.warning(
                "%s registry creation failed for cred_def_id: %s, error: %s",
                registry_type.title(),
                payload.cred_def_id,
                payload.error_msg,
            )

            # Handle retry
            if payload.should_retry and payload.retry_count < self.MAX_RETRY_COUNT:  # ✅
                LOGGER.info(
                    "Retrying %s registry creation, attempt %d",
                    registry_type,
                    payload.retry_count + 1,
                )

                new_options = payload.options.copy()
                new_options["retry_count"] = payload.retry_count + 1

                revoc = AnonCredsRevocation(profile)

                await revoc.emit_create_revocation_registry_definition_event(
                    issuer_id=payload.issuer_id,
                    cred_def_id=payload.cred_def_id,
                    registry_type=payload.registry_type,
                    tag=payload.tag,
                    max_cred_num=payload.max_cred_num,
                    options=new_options,
                )
            else:
                # Not retryable, so notify issuer about failure
                LOGGER.error(
                    "%s %s registry creation for cred def: %s",
                    "Max retries exceeded for" if payload.should_retry else "Won't retry",
                    registry_type,
                    payload.cred_def_id,
                )
                # TODO: Implement notification to issuer about failure
        else:  # ✅
            # Handle success - emit store request event
            revoc = AnonCredsRevocation(profile)
            await revoc.emit_store_revocation_registry_definition_event(
                rev_reg_def=payload.rev_reg_def,
                rev_reg_def_result=payload.rev_reg_def_result,
                rev_reg_def_private=payload.rev_reg_def_private,
                options=payload.options,
            )

    async def on_registry_store_requested(
        self, profile: Profile, event: RevRegDefStoreRequestedEvent
    ) -> None:
        """Handle registry store request."""
        payload = event.payload
        revoc = AnonCredsRevocation(profile)

        await revoc.handle_store_revocation_registry_definition_request(
            rev_reg_def_result=payload.rev_reg_def_result,
            rev_reg_def_private=payload.rev_reg_def_private,
            options=payload.options,
        )

    async def on_registry_store_response(
        self, profile: Profile, event: RevRegDefStoreResponseEvent
    ) -> None:
        """Handle registry store response."""
        payload = event.payload

        if payload.error_msg:
            # Handle failure
            LOGGER.warning(
                "Registry store failed for: %s, tag: %s, error: %s",
                payload.rev_reg_def_id,
                payload.tag,
                payload.error_msg,
            )

            # Implement retry logic
            if payload.should_retry and payload.retry_count < self.MAX_RETRY_COUNT:
                LOGGER.info(
                    "Retrying registry store, attempt %d", payload.retry_count + 1
                )

                new_options = payload.options.copy()
                new_options["retry_count"] = payload.retry_count + 1

                revoc = AnonCredsRevocation(profile)
                await revoc.handle_store_revocation_registry_definition_request(
                    rev_reg_def_result=payload.rev_reg_def_result,
                    rev_reg_def_private=payload.rev_reg_def_private,
                    options=new_options,
                )
            else:
                LOGGER.error(
                    "%s registry store for: %s, tag: %s",
                    "Max retries exceeded for" if payload.should_retry else "Won't retry",
                    payload.rev_reg_def_id,
                    payload.tag,
                )
                # TODO: Implement notification to issuer about failure
        else:
            # Handle success
            LOGGER.info(
                "Registry store succeeded for: %s, tag: %s",
                payload.rev_reg_def_id,
                payload.tag,
            )

            # Emit finished event
            revoc = AnonCredsRevocation(profile)
            state = payload.rev_reg_def_result.revocation_registry_definition_state
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
                    options=payload.options,
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
                    options=payload.options,
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

        LOGGER.debug("Handling tails upload request for: %s", payload.rev_reg_def_id)

        await revoc.handle_tails_upload_request(
            rev_reg_def_id=payload.rev_reg_def_id,
            rev_reg_def=payload.rev_reg_def,
            options=payload.options,
        )

    async def on_tails_upload_response(
        self, profile: Profile, event: TailsUploadResponseEvent
    ) -> None:
        """Handle tails upload response."""
        payload = event.payload

        if payload.error_msg:
            # Handle failure
            LOGGER.error(
                "Tails upload failed for: %s, error: %s",
                payload.rev_reg_def_id,
                payload.error_msg,
            )

            # Implement retry logic
            if payload.retry_count < self.MAX_RETRY_COUNT:
                LOGGER.info("Retrying tails upload, attempt %d", payload.retry_count + 1)

                new_options = payload.options.copy()
                new_options["retry_count"] = payload.retry_count + 1

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
                # TODO: Implement notification to issuer about failure
        else:
            # Handle success
            LOGGER.info("Tails upload succeeded for: %s", payload.rev_reg_def_id)

            # Request revocation list creation
            revoc = AnonCredsRevocation(profile)
            await revoc.emit_create_and_register_revocation_list_event(
                rev_reg_def_id=payload.rev_reg_def_id,
                options=payload.options,
            )

    async def on_rev_list_create_requested(
        self, profile: Profile, event: RevListCreateRequestedEvent
    ) -> None:
        """Handle revocation list creation request."""
        payload = event.payload
        revoc = AnonCredsRevocation(profile)

        LOGGER.debug(
            "Handling revocation list creation request for: %s",
            payload.rev_reg_def_id,
        )

        await revoc.create_and_register_revocation_list(
            rev_reg_def_id=payload.rev_reg_def_id,
            options=payload.options,
        )

    async def on_rev_list_create_response(
        self, profile: Profile, event: RevListCreateResponseEvent
    ) -> None:
        """Handle revocation list creation response."""
        payload = event.payload

        if payload.error_msg:
            # Handle failure
            LOGGER.error(
                "Revocation list creation failed for: %s, error: %s",
                payload.rev_reg_def_id,
                payload.error_msg,
            )

            # Implement retry logic
            if payload.retry_count < self.MAX_RETRY_COUNT:
                LOGGER.info(
                    "Retrying revocation list creation, attempt %d",
                    payload.retry_count + 1,
                )

                new_options = payload.options.copy()
                new_options["retry_count"] = payload.retry_count + 1

                revoc = AnonCredsRevocation(profile)
                await revoc.emit_create_and_register_revocation_list_event(
                    payload.rev_reg_def_id, new_options
                )
            else:
                LOGGER.error(
                    "Max retries exceeded for revocation list creation: %s",
                    payload.rev_reg_def_id,
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
                options=payload.options,
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

        LOGGER.debug(
            "Handling revocation list store request for: %s",
            payload.rev_reg_def_id,
        )

        await revoc.handle_store_revocation_list_request(
            rev_reg_def_id=payload.rev_reg_def_id,
            result=payload.result,
            options=payload.options,
        )

    async def on_rev_list_store_response(
        self, profile: Profile, event: RevListStoreResponseEvent
    ) -> None:
        """Handle revocation list store response."""
        payload = event.payload

        if payload.error_msg:
            # Handle failure
            LOGGER.error(
                "Revocation list store failed for: %s, error: %s",
                payload.rev_reg_def_id,
                payload.error_msg,
            )

            # Implement retry logic
            if payload.should_retry and payload.retry_count < self.MAX_RETRY_COUNT:
                LOGGER.info(
                    "Retrying revocation list store, attempt %d",
                    payload.retry_count + 1,
                )

                new_options = payload.options.copy()
                new_options["retry_count"] = payload.retry_count + 1

                revoc = AnonCredsRevocation(profile)
                await revoc.handle_store_revocation_list_request(
                    rev_reg_def_id=payload.rev_reg_def_id,
                    result=payload.result,
                    options=new_options,
                )
            else:
                LOGGER.error(
                    "Max retries exceeded for revocation list store: %s",
                    payload.rev_reg_def_id,
                )
                # TODO: Implement notification to issuer about failure
        else:
            # Handle success
            LOGGER.info("Revocation list store succeeded for: %s", payload.rev_reg_def_id)

            # If this is for the first registry, activate it
            revoc = AnonCredsRevocation(profile)
            options = payload.options.copy()
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

        LOGGER.debug(
            "Handling registry activation request for: %s", payload.rev_reg_def_id
        )

        await revoc.handle_activate_registry_request(
            rev_reg_def_id=payload.rev_reg_def_id,
            options=payload.options,
        )

    async def on_registry_activation_response(
        self, profile: Profile, event: RevRegActivationResponseEvent
    ) -> None:
        """Handle registry activation response."""
        payload = event.payload

        if payload.error_msg:
            # Handle failure
            LOGGER.error(
                "Registry activation failed for: %s, error: %s",
                payload.rev_reg_def_id,
                payload.error_msg,
            )

            # Implement retry logic
            if payload.retry_count < self.MAX_RETRY_COUNT:
                LOGGER.info(
                    "Retrying registry activation, attempt %d", payload.retry_count + 1
                )

                new_options = payload.options.copy()
                new_options["retry_count"] = payload.retry_count + 1

                revoc = AnonCredsRevocation(profile)
                await revoc.emit_set_active_registry_event(
                    payload.rev_reg_def_id, new_options
                )
            else:
                LOGGER.error(
                    "Max retries exceeded for registry activation: %s",
                    payload.rev_reg_def_id,
                )
                # TODO: Implement notification to issuer about failure
        else:
            # Handle success
            LOGGER.info("Registry activation succeeded for: %s", payload.rev_reg_def_id)

    async def on_registry_full_detected(
        self, profile: Profile, event: RevRegFullDetectedEvent
    ) -> None:
        """Handle registry full detection."""
        payload = event.payload
        revoc = AnonCredsRevocation(profile)

        LOGGER.info("Full registry detected: %s", payload.rev_reg_def_id)

        # Start the full registry handling process
        await revoc.handle_full_registry_event(
            rev_reg_def_id=payload.rev_reg_def_id,
            cred_def_id=payload.cred_def_id,
            options=payload.options,
        )

    async def on_registry_full_handling_started(
        self, profile: Profile, event: RevRegFullHandlingStartedEvent
    ) -> None:
        """Handle registry full handling started."""
        payload = event.payload

        LOGGER.info("Full registry handling started for: %s", payload.rev_reg_def_id)

    async def on_registry_full_handling_completed(
        self, profile: Profile, event: RevRegFullHandlingCompletedEvent
    ) -> None:
        """Handle registry full handling completed."""
        payload = event.payload

        LOGGER.info(
            "Full registry handling completed. Old: %s, New Active: %s",
            payload.old_rev_reg_def_id,
            payload.new_active_rev_reg_def_id,
        )

    async def on_registry_full_handling_failed(
        self, profile: Profile, event: RevRegFullHandlingFailedEvent
    ) -> None:
        """Handle registry full handling failure."""
        payload = event.payload

        LOGGER.error(
            "Full registry handling failed for: %s, error: %s",
            payload.rev_reg_def_id,
            payload.error,
        )

        # Implement retry logic
        if payload.retry_count < self.MAX_RETRY_COUNT:
            LOGGER.info(
                "Retrying full registry handling, attempt %d",
                payload.retry_count + 1,
            )

            new_options = payload.options.copy()
            new_options["retry_count"] = payload.retry_count + 1

            revoc = AnonCredsRevocation(profile)
            await revoc.handle_full_registry_event(
                rev_reg_def_id=payload.rev_reg_def_id,
                cred_def_id=payload.cred_def_id,
                options=new_options,
            )
        else:
            LOGGER.error(
                "Max retries exceeded for full registry handling: %s",
                payload.rev_reg_def_id,
            )
            # TODO: Implement notification to issuer about failure

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

    async def _should_retry_operation(
        self,
        retry_count: int,
        error_msg: str,
        operation_type: str,
    ) -> bool:
        """Determine if an operation should be retried.

        Args:
            retry_count (int): Current retry count
            error_msg (str): Error message
            operation_type (str): Type of operation

        Returns:
            bool: Whether to retry the operation

        """
        # Basic retry logic - can be enhanced with more sophisticated logic
        if retry_count >= self.MAX_RETRY_COUNT:
            return False

        # Don't retry certain types of errors
        non_retryable_errors = [
            "credential definition not found",
            "invalid parameters",
            "permission denied",
        ]

        for non_retryable in non_retryable_errors:
            if non_retryable.lower() in error_msg.lower():
                return False

        return True
