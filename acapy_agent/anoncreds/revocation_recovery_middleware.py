"""Middleware for revocation event recovery during admin requests."""

import asyncio
import logging
from typing import Coroutine, Set

from aiohttp import web

from acapy_agent.core.profile import Profile

from ..admin.request_context import AdminRequestContext
from ..core.event_bus import EventBus
from ..storage.base import BaseStorage
from ..storage.error import StorageNotFoundError
from ..storage.type import (
    RECORD_TYPE_REV_LIST_CREATE_EVENT,
    RECORD_TYPE_REV_LIST_STORE_EVENT,
    RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
    RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
    RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
    RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
    RECORD_TYPE_TAILS_UPLOAD_EVENT,
)
from .event_recovery import EventRecoveryManager

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


async def has_in_progress_revocation_events(profile: Profile) -> bool:
    """Check if profile has any in-progress revocation events.

    Args:
        profile: The profile to check

    Returns:
        True if there are in-progress events, False otherwise
    """
    try:
        async with profile.session() as session:
            storage = session.inject(BaseStorage)

            # Check each event type for in-progress records
            event_types = [
                RECORD_TYPE_REV_REG_DEF_CREATE_EVENT,
                RECORD_TYPE_REV_REG_DEF_STORE_EVENT,
                RECORD_TYPE_TAILS_UPLOAD_EVENT,
                RECORD_TYPE_REV_LIST_CREATE_EVENT,
                RECORD_TYPE_REV_LIST_STORE_EVENT,
                RECORD_TYPE_REV_REG_ACTIVATION_EVENT,
                RECORD_TYPE_REV_REG_FULL_HANDLING_EVENT,
            ]

            for event_type in event_types:
                try:
                    records = await storage.find_all_records(
                        type_filter=event_type, tag_query={"state": "requested"}
                    )
                    if records:
                        return True
                except StorageNotFoundError:
                    # No records of this type, continue
                    pass
                except Exception as e:
                    LOGGER.warning(
                        "Error checking for in-progress events of type %s: %s",
                        event_type,
                        str(e),
                    )

            return False
    except Exception as e:
        LOGGER.error("Error checking for in-progress revocation events: %s", str(e))
        return False


async def recover_profile_events(profile: Profile, event_bus: EventBus) -> None:
    """Recover in-progress events for a specific profile.

    Args:
        profile: The profile to recover events for
        event_bus: The event bus to re-emit events on
    """
    # Get recovery timeout from settings
    recovery_timeout = profile.settings.get_int(
        "anoncreds.revocation.recovery_timeout_seconds", 30
    )

    try:
        recovery_manager = EventRecoveryManager(profile, event_bus)

        # Use asyncio.wait_for to implement timeout
        recovered_count = await asyncio.wait_for(
            recovery_manager.recover_in_progress_events(), timeout=recovery_timeout
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
    except (KeyError, AttributeError):
        # No profile context available, skip recovery
        return await handler(request)

    # Check if automatic revocation recovery is enabled
    auto_recovery_enabled = profile.settings.get_bool(
        "anoncreds.revocation.auto_recovery_enabled", True
    )

    if not auto_recovery_enabled:
        return await handler(request)

    # Check if we've already recovered this profile
    if recovery_tracker.is_recovered(profile_name):
        return await handler(request)

    # Check if recovery is already in progress for this profile
    if recovery_tracker.is_recovery_in_progress(profile_name):
        LOGGER.debug(
            "Recovery in progress for profile %s, proceeding with request",
            profile_name,
        )
        return await handler(request)

    # Check if profile has any in-progress revocation events
    try:
        if not await has_in_progress_revocation_events(profile):
            # No events to recover, mark as recovered
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
    recovery_tracker.mark_recovery_started(profile_name)

    try:
        # Get event bus from profile context
        try:
            event_bus = context.profile.inject(EventBus)
        except Exception as e:
            LOGGER.error(
                "Failed to inject EventBus for profile %s: %s", profile_name, str(e)
            )
            recovery_tracker.mark_recovery_failed(profile_name)
            return await handler(request)

        # Perform recovery with timeout protection
        try:
            await recover_profile_events(profile, event_bus)
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
        recovery_tracker.mark_recovery_completed(profile_name)

        LOGGER.info("Revocation event recovery completed for profile %s", profile_name)

    except Exception as e:
        # Catch-all for any unexpected errors
        recovery_tracker.mark_recovery_failed(profile_name)

        LOGGER.error(
            "Unexpected error in revocation event recovery for profile %s: %s",
            profile_name,
            str(e),
        )

        # Continue with request despite recovery failure
        # This ensures recovery issues don't block normal operations

    return await handler(request)
