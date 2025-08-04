"""Middleware for revocation event recovery during admin requests."""

import asyncio
import logging
import os
from typing import Coroutine, Optional, Set

from aiohttp import web

from acapy_agent.core.profile import Profile

from ..admin.request_context import AdminRequestContext
from ..core.event_bus import EventBus
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


async def has_in_progress_revocation_events(
    profile: Profile, min_age_seconds: Optional[int] = None
) -> bool:
    """Check if profile has any in-progress revocation events.

    Args:
        profile: The profile to check
        min_age_seconds: Only consider events older than this many seconds

    Returns:
        True if there are in-progress events (filtered by age), False otherwise
    """
    try:
        async with profile.session() as session:
            event_storage = EventStorageManager(session)

            # Use EventStorageManager to get in-progress events with age filtering
            in_progress_events = await event_storage.get_in_progress_events(
                min_age_seconds=min_age_seconds
            )

            return len(in_progress_events) > 0

    except Exception as e:
        LOGGER.error("Error checking for in-progress revocation events: %s", str(e))
        return False


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

    # Check if profile has any in-progress revocation events (older than delay)
    LOGGER.debug(
        "Checking for in-progress revocation events for profile %s (older than %d secs)",
        profile_name,
        recovery_delay_seconds,
    )
    try:
        if not await has_in_progress_revocation_events(profile, recovery_delay_seconds):
            # No events to recover, mark as recovered
            LOGGER.debug(
                "No recoverable in-progress events found for profile %s", profile_name
            )
            recovery_tracker.mark_recovery_completed(profile_name)
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
        LOGGER.debug("Beginning event recovery for profile %s", profile_name)
        try:
            await recover_profile_events(profile, event_bus, recovery_delay_seconds)
            LOGGER.debug(
                "Event recovery completed successfully for profile %s", profile_name
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
