"""Event recovery manager for anoncreds revocation registry management."""

import logging
from typing import Dict

from ..core.event_bus import EventBus
from ..core.profile import Profile
from ..storage.type import (
    RECORD_TYPE_REV_LIST_CREATE_EVENT,
    RECORD_TYPE_REV_LIST_STORE_EVENT,
    RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
    RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
    RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
    RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
    RECORD_TYPE_TAILS_UPLOAD_EVENT,
)
from .event_storage import EventStorageManager, deserialize_event_payload
from .events import (
    RevListCreateRequestedEvent,
    RevListCreateRequestedPayload,
    RevListStoreRequestedEvent,
    RevListStoreRequestedPayload,
    RevRegActivationRequestedEvent,
    RevRegActivationRequestedPayload,
    RevRegDefCreateRequestedEvent,
    RevRegDefCreateRequestedPayload,
    RevRegDefStoreRequestedEvent,
    RevRegDefStoreRequestedPayload,
    RevRegFullDetectedEvent,
    RevRegFullDetectedPayload,
    TailsUploadRequestedEvent,
    TailsUploadRequestedPayload,
)

LOGGER = logging.getLogger(__name__)


class EventRecoveryManager:
    """Manages recovery of in-progress events during agent startup."""

    def __init__(self, profile: Profile, event_bus: EventBus):
        """Initialize the EventRecoveryManager.

        Args:
            profile: The profile to use for recovery operations
            event_bus: The event bus to re-emit events on
        """
        self.profile = profile
        self.event_bus = event_bus

    async def recover_in_progress_events(self) -> int:
        """Recover all in-progress events by re-emitting them.

        Returns:
            Number of events recovered
        """
        recovered_count = 0

        async with self.profile.session() as session:
            event_storage = EventStorageManager(session)

            # Get all in-progress events
            in_progress_events = await event_storage.get_in_progress_events()

            LOGGER.info("Found %d in-progress events to recover", len(in_progress_events))

            for event_record in in_progress_events:
                LOGGER.debug(
                    "Recovering %s event: %s", event_record["event_type"], event_record
                )
                try:
                    await self._recover_single_event(event_record)
                    recovered_count += 1
                except Exception:
                    LOGGER.exception(
                        "Failed to recover event %s (correlation_id: %s): %s",
                        event_record["event_type"],
                        event_record["correlation_id"],
                    )

        if recovered_count > 0:
            LOGGER.info("Successfully recovered %d events", recovered_count)
        else:
            LOGGER.debug("No events needed recovery")

        return recovered_count

    async def _recover_single_event(self, event_record: Dict) -> None:
        """Recover a single event by re-emitting it.

        Args:
            event_record: The event record to recover
        """
        event_type = event_record["event_type"]
        event_data = event_record["event_data"]
        correlation_id = event_record["correlation_id"]
        options = event_record["options"]

        # Add recovery flag to options
        recovery_options = options.copy()
        recovery_options["recovery"] = True
        recovery_options["correlation_id"] = correlation_id

        LOGGER.debug(
            "Recovering event %s with correlation_id: %s. Event data: %s",
            event_type,
            correlation_id,
            event_data,
        )

        # Map event types to their corresponding event classes and re-emit
        if event_type == RECORD_TYPE_REV_REG_DEF_CREATE_EVENT:
            await self._recover_rev_reg_def_create_event(event_data, recovery_options)
        elif event_type == RECORD_TYPE_REV_REG_DEF_STORE_EVENT:
            await self._recover_rev_reg_def_store_event(event_data, recovery_options)
        elif event_type == RECORD_TYPE_TAILS_UPLOAD_EVENT:
            await self._recover_tails_upload_event(event_data, recovery_options)
        elif event_type == RECORD_TYPE_REV_LIST_CREATE_EVENT:
            await self._recover_rev_list_create_event(event_data, recovery_options)
        elif event_type == RECORD_TYPE_REV_LIST_STORE_EVENT:
            await self._recover_rev_list_store_event(event_data, recovery_options)
        elif event_type == RECORD_TYPE_REV_REG_ACTIVATION_EVENT:
            await self._recover_rev_reg_activation_event(event_data, recovery_options)
        elif event_type == RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT:
            await self._recover_rev_reg_full_handling_event(event_data, recovery_options)
        else:
            LOGGER.warning("Unknown event type for recovery: %s", event_type)

    async def _recover_rev_reg_def_create_event(
        self, event_data: Dict, options: Dict
    ) -> None:
        """Recover a revocation registry definition create event."""
        payload = deserialize_event_payload(event_data, RevRegDefCreateRequestedPayload)

        # Update options with recovery context
        payload_options = payload.options.copy()
        payload_options.update(options)

        # Create new payload with updated options
        new_payload = RevRegDefCreateRequestedPayload(
            issuer_id=payload.issuer_id,
            cred_def_id=payload.cred_def_id,
            registry_type=payload.registry_type,
            tag=payload.tag,
            max_cred_num=payload.max_cred_num,
            options=payload_options,
        )

        event = RevRegDefCreateRequestedEvent(new_payload)
        await self.event_bus.notify(self.profile, event)

    async def _recover_rev_reg_def_store_event(
        self, event_data: Dict, options: Dict
    ) -> None:
        """Recover a revocation registry definition store event."""
        payload = deserialize_event_payload(event_data, RevRegDefStoreRequestedPayload)

        # Update options with recovery context
        payload_options = payload.options.copy()
        payload_options.update(options)

        # Create new payload with updated options
        new_payload = RevRegDefStoreRequestedPayload(
            rev_reg_def=payload.rev_reg_def,
            rev_reg_def_result=payload.rev_reg_def_result,
            rev_reg_def_private=payload.rev_reg_def_private,
            options=payload_options,
        )

        event = RevRegDefStoreRequestedEvent(new_payload)
        await self.event_bus.notify(self.profile, event)

    async def _recover_tails_upload_event(self, event_data: Dict, options: Dict) -> None:
        """Recover a tails upload event."""
        payload = deserialize_event_payload(event_data, TailsUploadRequestedPayload)

        # Update options with recovery context
        payload_options = payload.options.copy()
        payload_options.update(options)

        # Create new payload with updated options
        new_payload = TailsUploadRequestedPayload(
            rev_reg_def_id=payload.rev_reg_def_id,
            rev_reg_def=payload.rev_reg_def,
            options=payload_options,
        )

        event = TailsUploadRequestedEvent(new_payload)
        await self.event_bus.notify(self.profile, event)

    async def _recover_rev_list_create_event(
        self, event_data: Dict, options: Dict
    ) -> None:
        """Recover a revocation list create event."""
        payload = deserialize_event_payload(event_data, RevListCreateRequestedPayload)

        # Update options with recovery context
        payload_options = payload.options.copy()
        payload_options.update(options)

        # Create new payload with updated options
        new_payload = RevListCreateRequestedPayload(
            rev_reg_def_id=payload.rev_reg_def_id,
            options=payload_options,
        )

        event = RevListCreateRequestedEvent(new_payload)
        await self.event_bus.notify(self.profile, event)

    async def _recover_rev_list_store_event(
        self, event_data: Dict, options: Dict
    ) -> None:
        """Recover a revocation list store event."""
        payload = deserialize_event_payload(event_data, RevListStoreRequestedPayload)

        # Update options with recovery context
        payload_options = payload.options.copy()
        payload_options.update(options)

        # Create new payload with updated options
        new_payload = RevListStoreRequestedPayload(
            rev_reg_def_id=payload.rev_reg_def_id,
            result=payload.result,
            options=payload_options,
        )

        event = RevListStoreRequestedEvent(new_payload)
        await self.event_bus.notify(self.profile, event)

    async def _recover_rev_reg_activation_event(
        self, event_data: Dict, options: Dict
    ) -> None:
        """Recover a revocation registry activation event."""
        payload = deserialize_event_payload(event_data, RevRegActivationRequestedPayload)

        # Update options with recovery context
        payload_options = payload.options.copy()
        payload_options.update(options)

        # Create new payload with updated options
        new_payload = RevRegActivationRequestedPayload(
            rev_reg_def_id=payload.rev_reg_def_id,
            options=payload_options,
        )

        event = RevRegActivationRequestedEvent(new_payload)
        await self.event_bus.notify(self.profile, event)

    async def _recover_rev_reg_full_handling_event(
        self, event_data: Dict, options: Dict
    ) -> None:
        """Recover a revocation registry full handling event."""
        payload = deserialize_event_payload(event_data, RevRegFullDetectedPayload)

        # Update options with recovery context
        payload_options = payload.options.copy()
        payload_options.update(options)

        # Create new payload with updated options
        new_payload = RevRegFullDetectedPayload(
            rev_reg_def_id=payload.rev_reg_def_id,
            cred_def_id=payload.cred_def_id,
            options=payload_options,
        )

        event = RevRegFullDetectedEvent(new_payload)
        await self.event_bus.notify(self.profile, event)

    async def cleanup_old_events(self, max_age_hours: int = 24) -> int:
        """Clean up old completed events.

        Args:
            max_age_hours: Maximum age in hours before cleanup

        Returns:
            Number of events cleaned up
        """
        async with self.profile.session() as session:
            event_storage = EventStorageManager(session)
            return await event_storage.cleanup_completed_events(
                max_age_hours=max_age_hours
            )

    async def get_recovery_status(self) -> Dict:
        """Get the current recovery status.

        Returns:
            Dictionary containing recovery status information
        """
        async with self.profile.session() as session:
            event_storage = EventStorageManager(session)

            in_progress_events = await event_storage.get_in_progress_events()
            failed_events = await event_storage.get_failed_events()

            status = {
                "in_progress_events": len(in_progress_events),
                "failed_events": len(failed_events),
                "events_by_type": {},
                "failed_events_by_type": {},
            }

            # Count events by type
            for event in in_progress_events:
                event_type = event["event_type"]
                if event_type not in status["events_by_type"]:
                    status["events_by_type"][event_type] = 0
                status["events_by_type"][event_type] += 1

            for event in failed_events:
                event_type = event["event_type"]
                if event_type not in status["failed_events_by_type"]:
                    status["failed_events_by_type"][event_type] = 0
                status["failed_events_by_type"][event_type] += 1

            return status


async def recover_revocation_events(profile: Profile, event_bus: EventBus) -> int:
    """Convenience function to recover revocation events.

    Args:
        profile: The profile to use for recovery
        event_bus: The event bus to re-emit events on

    Returns:
        Number of events recovered
    """
    recovery_manager = EventRecoveryManager(profile, event_bus)
    return await recovery_manager.recover_in_progress_events()
