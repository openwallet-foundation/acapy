"""Middleware for revocation event recovery during admin requests."""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Coroutine, Optional, Set, Tuple

from aiohttp import web

from acapy_agent.core.profile import Profile

from ..admin.request_context import AdminRequestContext
from ..core.event_bus import EventBus
from ..messaging.util import str_to_datetime
from .event_recovery import EventRecoveryManager
from .event_storage import EventStorageManager

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
    profile: Profile, min_age_seconds: Optional[int] = None
) -> Tuple[int, int]:
    """Get counts of pending and recoverable revocation events.

    This function fetches all in-progress events once and calculates both
    pending events (all events) and recoverable events (events older than
    min_age_seconds) from the same dataset.

    Args:
        profile: The profile to check
        min_age_seconds: Only consider events older than this many seconds as recoverable

    Returns:
        Tuple of (pending_count, recoverable_count) where:
        - pending_count: Total number of in-progress events (regardless of age)
        - recoverable_count: Number of in-progress events older than min_age_seconds
    """
    try:
        async with profile.session() as session:
            event_storage = EventStorageManager(session)

            # Get all in-progress events without age filtering
            all_events = await event_storage.get_in_progress_events(min_age_seconds=None)
            pending_count = len(all_events)

            if min_age_seconds is not None and pending_count > 0:
                # Calculate recoverable count by filtering the already-fetched events
                # This is more efficient than making another database query
                cutoff_time = datetime.now(timezone.utc) - timedelta(
                    seconds=min_age_seconds
                )
                recoverable_count = 0

                for event in all_events:
                    if event.get("created_at"):
                        try:
                            event_created_at = str_to_datetime(event["created_at"])
                            if event_created_at <= cutoff_time:
                                recoverable_count += 1
                        except (ValueError, KeyError) as e:
                            LOGGER.warning(
                                "Failed to parse created_at for event %s: %s",
                                event.get("correlation_id", "unknown"),
                                str(e),
                            )
                            # For events without valid timestamps, consider them
                            # recoverable
                            recoverable_count += 1
                    else:
                        # For events without timestamps, consider them recoverable
                        LOGGER.warning(
                            "Event %s has no created_at, considering it recoverable",
                            event.get("correlation_id", "unknown"),
                        )
                        recoverable_count += 1
            else:
                # If no age filter, all pending events are recoverable
                recoverable_count = pending_count

            if pending_count > 0:
                LOGGER.debug(
                    "Found %d pending revocation events (%d recoverable) for profile %s",
                    pending_count,
                    recoverable_count,
                    profile.name,
                )

            return pending_count, recoverable_count

    except Exception as e:
        LOGGER.error("Error checking for revocation events: %s", str(e))
        return 0, 0


async def recover_profile_events(
    profile: Profile, event_bus: EventBus, recovery_delay_seconds: int = 30
) -> None:
    """Recover in-progress events for a specific profile.

    Args:
        profile: The profile to recover events for
        event_bus: The event bus to re-emit events on
        recovery_delay_seconds: Only recover events older than this many seconds
    """
    # Get recovery timeout from settings
    recovery_timeout = profile.settings.get_int(
        "anoncreds.revocation.recovery_timeout_seconds", 30
    )

    try:
        recovery_manager = EventRecoveryManager(profile, event_bus)

        # Use asyncio.wait_for to implement timeout
        recovered_count = await asyncio.wait_for(
            recovery_manager.recover_in_progress_events(
                min_age_seconds=recovery_delay_seconds
            ),
            timeout=recovery_timeout,
        )

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
    except asyncio.TimeoutError:
        LOGGER.error(
            "Recovery timeout (%d seconds) exceeded for profile %s",
            recovery_timeout,
            profile.name,
        )
        raise
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
        "anoncreds.revocation.auto_recovery_enabled", default=True
    )
    LOGGER.debug(
        "Auto recovery enabled for profile %s: %s", profile_name, auto_recovery_enabled
    )

    if not auto_recovery_enabled:
        LOGGER.debug("Auto recovery disabled for profile %s", profile_name)
        return await handler(request)

    # Get recovery delay setting
    recovery_delay_seconds = int(
        os.getenv("ANONCREDS_REVOCATION_RECOVERY_DELAY_SECONDS", "30")
    )
    LOGGER.debug(
        "Recovery delay for profile %s: %d seconds", profile_name, recovery_delay_seconds
    )

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

    # Check if profile has any in-progress revocation events
    LOGGER.debug(
        "Checking for revocation events for profile %s (recovery delay: %d secs)",
        profile_name,
        recovery_delay_seconds,
    )
    try:
        pending_count, recoverable_count = await get_revocation_event_counts(
            profile, recovery_delay_seconds
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
                return await handler(request)
            else:
                # There are pending events within the delay period
                # - don't mark as recovered yet
                LOGGER.debug(
                    "Found %d pending events within recovery delay for profile %s, "
                    "not marking as recovered yet",
                    pending_count,
                    profile_name,
                )
                return await handler(request)

    except Exception as e:
        LOGGER.error(
            "Error checking for in-progress events for profile %s: %s",
            profile_name,
            str(e),
        )
        # Continue with request on error
        return await handler(request)

    # Mark recovery as started
    LOGGER.debug("Starting recovery process for profile %s", profile_name)
    recovery_tracker.mark_recovery_started(profile_name)

    try:
        # Get event bus from profile context
        LOGGER.debug("Injecting EventBus for profile %s", profile_name)
        try:
            event_bus = context.profile.inject(EventBus)
            LOGGER.debug("Successfully injected EventBus for profile %s", profile_name)
        except Exception as e:
            LOGGER.error(
                "Failed to inject EventBus for profile %s: %s", profile_name, str(e)
            )
            recovery_tracker.mark_recovery_failed(profile_name)
            return await handler(request)

        # Perform recovery with timeout protection
        LOGGER.debug(
            "Beginning recovery of events older than %d seconds for profile %s",
            recovery_delay_seconds,
            profile_name,
        )
        try:
            await recover_profile_events(profile, event_bus, recovery_delay_seconds)
            LOGGER.debug(
                "Recovery of recoverable events completed successfully for profile %s",
                profile_name,
            )
        except asyncio.TimeoutError:
            LOGGER.error(
                "Revocation event recovery timed out for profile %s", profile_name
            )
            recovery_tracker.mark_recovery_failed(profile_name)
            return await handler(request)
        except Exception as e:
            LOGGER.error(
                "Revocation event recovery failed for profile %s: %s",
                profile_name,
                str(e),
            )
            recovery_tracker.mark_recovery_failed(profile_name)
            return await handler(request)

        # Mark recovery as completed
        LOGGER.debug("Marking recovery as completed for profile %s", profile_name)
        recovery_tracker.mark_recovery_completed(profile_name)

        LOGGER.info("Revocation event recovery completed for profile %s", profile_name)

    except Exception as e:
        # Catch-all for any unexpected errors
        LOGGER.debug(
            "Marking recovery as failed due to unexpected error for profile %s",
            profile_name,
        )
        recovery_tracker.mark_recovery_failed(profile_name)

        LOGGER.error(
            "Unexpected error in revocation event recovery for profile %s: %s",
            profile_name,
            str(e),
        )

        # Continue with request despite recovery failure
        # This ensures recovery issues don't block normal operations

    LOGGER.debug("Proceeding with original request for profile %s", profile_name)
    return await handler(request)
