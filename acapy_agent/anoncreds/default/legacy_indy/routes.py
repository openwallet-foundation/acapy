"""Routes for Legacy Indy Registry."""

import logging
import re

from ....core.event_bus import EventBus, EventWithMetadata
from ....core.profile import Profile
from ...events import REV_LIST_ENDORSED_UPDATE_FAILED_EVENT
from .recover import fix_and_publish_from_invalid_accum_err

LOGGER = logging.getLogger(__name__)


def register_events(event_bus: EventBus):
    """Subscribe to any events we need to support."""
    # If revocation list requires endorsement and fails to update, this event is emitted
    # to trigger retry logic and notify of failure
    event_bus.subscribe(
        re.compile(REV_LIST_ENDORSED_UPDATE_FAILED_EVENT),
        notify_issuer_about_update_failure_due_to_endorsement,
    )


async def notify_issuer_about_update_failure_due_to_endorsement(
    profile: Profile,
    event: EventWithMetadata,
) -> None:
    """Notify issuer about a failure that couldn't be automatically recovered.

    Args:
        profile (Profile): The profile context
        event (EventWithMetadata): Failure message describing the endorsement failure

    """
    await fix_and_publish_from_invalid_accum_err(profile, event.payload["msg"])
