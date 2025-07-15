"""Middleware for revocation event recovery during admin requests."""

import asyncio
import logging
from typing import Coroutine, Set, Tuple

from aiohttp import web

from acapy_agent.core.profile import Profile

from ..admin.request_context import AdminRequestContext
from ..core.event_bus import EventBus
from .event_recovery import EventRecoveryManager
from .event_storage import EventStorageManager
from .retry_utils import is_event_expired

LOGGER = logging.getLogger(__name__)


class RevocationRecoveryTracker:
    """Tracks revocation recovery state across server session."""

    def __init__(self):
        """Initialize the revocation recovery tracker."""
        self.recovered_profiles: Set[str] = set()
        self.recovery_in_progress: Set[str] = set()

    def is_recovered(self, profile_name: str) -> bool:
        """Check if profile has already been recovered."""
        return profile_name in self.recovered_profiles

    def is_recovery_in_progress(self, profile_name: str) -> bool:
        """Check if recovery is currently in progress for profile."""
        return profile_name in self.recovery_in_progress

    def mark_recovery_started(self, profile_name: str) -> None:
        """Mark recovery as started for profile."""
        self.recovery_in_progress.add(profile_name)

    def mark_recovery_completed(self, profile_name: str) -> None:
        """Mark recovery as completed for profile."""
        self.recovery_in_progress.discard(profile_name)
        self.recovered_profiles.add(profile_name)

    def mark_recovery_failed(self, profile_name: str) -> None:
        """Mark recovery as failed for profile."""
        self.recovery_in_progress.discard(profile_name)
        # Don't add to recovered_profiles so it can be retried


# Global recovery tracker instance
recovery_tracker = RevocationRecoveryTracker()


async def get_revocation_event_counts(
    profile: Profile, check_expiry: bool = True
) -> Tuple[int, int]:
    """Get counts of pending and recoverable revocation events.

    This function fetches all in-progress events once and calculates both
    pending events (all events) and recoverable events (events past their expiry).

    Args:
        profile: The profile to check
        check_expiry: If True, separate expired from non-expired events

    Returns:
        Tuple of (pending_count, recoverable_count) where:
        - pending_count: Total number of in-progress events
        - recoverable_count: Number of in-progress events past their expiry timestamp

    """
    try:
        async with profile.session() as session:
            event_storage = EventStorageManager(session)

            # Get all in-progress events
            all_events = await event_storage.get_in_progress_events(only_expired=False)
            pending_count = len(all_events)

            if check_expiry and pending_count > 0:
                # Calculate recoverable count by checking expiry timestamps
                recoverable_count = 0

                for event in all_events:
                    expiry_timestamp = event.get("expiry_timestamp")
                    if expiry_timestamp:
                        if is_event_expired(expiry_timestamp):
                            recoverable_count += 1
                    else:
                        # For events without expiry timestamps, consider them recoverable
                        LOGGER.warning(
                            "Event %s has no expiry time, considering it recoverable",
                            event.get("correlation_id", "unknown"),
                        )
                        recoverable_count += 1
            else:
                # If not checking expiry, all pending events are recoverable
                recoverable_count = pending_count

            if pending_count > 0:
                LOGGER.debug(
                    "Found %d pending revocation events (%d recoverable) for profile %s",
                    pending_count,
                    recoverable_count,
                    profile.name,
                )

            return pending_count, recoverable_count

    except Exception:
        LOGGER.exception("Error checking for revocation events")
        return 0, 0


async def recover_profile_events(profile: Profile, event_bus: EventBus) -> None:
    """Recover in-progress events for a specific profile.

    Args:
        profile: The profile to recover events for
        event_bus: The event bus to re-emit events on

    """
    try:
        recovery_manager = EventRecoveryManager(profile, event_bus)

        recovered_count = await recovery_manager.recover_in_progress_events()

        if recovered_count > 0:
            LOGGER.info(
                "Recovered %d in-progress revocation events for profile %s",
                recovered_count,
                profile.name,
            )
        else:
            LOGGER.debug(
                "No in-progress revocation events found for profile %s", profile.name
            )
    except Exception as e:
        LOGGER.error(
            "Failed to recover revocation events for profile %s: %s", profile.name, str(e)
        )
        raise


@web.middleware
async def revocation_recovery_middleware(request: web.BaseRequest, handler: Coroutine):
    """Middleware for revocation registry event recovery.

    This middleware intercepts requests and checks if the tenant/profile
    has any in-progress revocation registry events that need to be recovered.
    Recovery is performed once per profile per server session.
    """
    # Skip recovery checks for certain endpoints that don't need it
    skip_paths = ["/status/"]

    request_path = str(request.rel_url)
    if any(request_path.startswith(skip_path) for skip_path in skip_paths):
        return await handler(request)

    # Get the profile context
    try:
        context: AdminRequestContext = request["context"]
        profile = context.profile
        profile_name = profile.name
        LOGGER.debug("Retrieved profile context for profile: %s", profile_name)
    except (KeyError, AttributeError):
        # No profile context available, skip recovery
        LOGGER.debug("No profile context available, skipping recovery")
        return await handler(request)

    # Check if automatic revocation recovery is enabled
    auto_recovery_enabled = profile.settings.get_bool(
        "anoncreds.revocation.auto_recovery_enabled", default=False
    )
    LOGGER.debug(
        "Auto recovery enabled for profile %s: %s", profile_name, auto_recovery_enabled
    )

    if not auto_recovery_enabled:
        LOGGER.debug("Auto recovery disabled for profile %s", profile_name)
        return await handler(request)

    # Check if we've already recovered this profile
    if recovery_tracker.is_recovered(profile_name):
        LOGGER.debug(
            "Profile %s already recovered, proceeding with request", profile_name
        )
        return await handler(request)

    # Check if recovery is already in progress for this profile
    if recovery_tracker.is_recovery_in_progress(profile_name):
        LOGGER.debug(
            "Recovery in progress for profile %s, proceeding with request",
            profile_name,
        )
        return await handler(request)

    # Flag to determine if we should proceed with the handler early. This is to avoid
    # calling handler within try/except blocks, which would catch handler HTTPExceptions
    should_proceed_with_handler = False

    # Check if profile has any in-progress revocation events
    LOGGER.debug("Checking in-progress revocation events for profile %s", profile_name)
    try:
        pending_count, recoverable_count = await get_revocation_event_counts(
            profile, check_expiry=True
        )

        if recoverable_count == 0:
            # No recoverable events found
            if pending_count == 0:
                # No events at all - mark as recovered
                LOGGER.debug(
                    "No pending or recoverable events found for profile %s, "
                    "marking as recovered",
                    profile_name,
                )
                recovery_tracker.mark_recovery_completed(profile_name)
                should_proceed_with_handler = True
            else:
                # There are pending events within the delay period
                # - don't mark as recovered yet
                LOGGER.debug(
                    "Found %d pending events within recovery delay for profile %s, "
                    "not marking as recovered yet",
                    pending_count,
                    profile_name,
                )
                should_proceed_with_handler = True

    except Exception as e:
        LOGGER.error(
            "Error checking for in-progress events for profile %s: %s",
            profile_name,
            str(e),
        )
        # Continue with request on error
        should_proceed_with_handler = True

    # If we should proceed with handler early, skip recovery process
    if should_proceed_with_handler:
        LOGGER.debug("Proceeding with original request for profile %s", profile_name)
        return await handler(request)

    # Mark recovery as started
    LOGGER.debug("Starting recovery process for profile %s", profile_name)
    recovery_tracker.mark_recovery_started(profile_name)

    try:
        # Get event bus from profile context
        event_bus = context.profile.inject(EventBus)

        # Perform recovery with timeout protection
        LOGGER.debug(
            "Beginning recovery of events older that have expired for profile %s",
            profile_name,
        )
        await recover_profile_events(profile, event_bus)
        LOGGER.debug(
            "Recovery of recoverable events completed successfully for profile %s",
            profile_name,
        )

        # Mark recovery as completed on success
        LOGGER.debug("Marking recovery as completed for profile %s", profile_name)
        recovery_tracker.mark_recovery_completed(profile_name)
        LOGGER.info("Revocation event recovery completed for profile %s", profile_name)
    except asyncio.TimeoutError:
        LOGGER.error("Revocation event recovery timed out for profile %s", profile_name)
        recovery_tracker.mark_recovery_failed(profile_name)
    except Exception as e:
        LOGGER.error(
            "Revocation event recovery failed for profile %s: %s", profile_name, str(e)
        )
        recovery_tracker.mark_recovery_failed(profile_name)

    # Final handler call - outside all try blocks to avoid HTTPFound being caught
    LOGGER.debug("Proceeding with original request for profile %s", profile_name)
    return await handler(request)
