"""Routes for revocation notification."""
import logging
import re

from ....core.event_bus import Event, EventBus
from ....core.profile import Profile
from ....messaging.responder import BaseResponder
from ....revocation.util import (
    REVOCATION_CLEAR_PENDING_EVENT,
    REVOCATION_PUBLISHED_EVENT,
    REVOCATION_EVENT_PREFIX,
)
from ....storage.error import StorageError, StorageNotFoundError
from .models.rev_notification_record import RevNotificationRecord

LOGGER = logging.getLogger(__name__)


def register_events(event_bus: EventBus):
    """Register to handle events."""
    event_bus.subscribe(
        re.compile(f"^{REVOCATION_EVENT_PREFIX}{REVOCATION_PUBLISHED_EVENT}.*"),
        on_revocation_published,
    )
    event_bus.subscribe(
        re.compile(f"^{REVOCATION_EVENT_PREFIX}{REVOCATION_CLEAR_PENDING_EVENT}.*"),
        on_pending_cleared,
    )


async def on_revocation_published(profile: Profile, event: Event):
    """Handle issuer revoke event."""
    LOGGER.debug("Sending notification of revocation to recipient: %s", event.payload)

    responder = profile.inject(BaseResponder)
    crids = event.payload.get("crids") or []

    try:
        async with profile.session() as session:
            records = await RevNotificationRecord.query_by_rev_reg_id(
                session,
                rev_reg_id=event.payload["rev_reg_id"],
            )
            records = [record for record in records if record.cred_rev_id in crids]

            for record in records:
                await record.delete_record(session)
                await responder.send(
                    record.to_message(), connection_id=record.connection_id
                )

    except StorageNotFoundError:
        LOGGER.info(
            "No revocation notification record found for revoked credential; "
            "no notification will be sent"
        )
    except StorageError:
        LOGGER.exception("Failed to retrieve revocation notification record")


async def on_pending_cleared(profile: Profile, event: Event):
    """Handle pending cleared event."""

    # Query by rev reg ID
    async with profile.session() as session:
        notifications = await RevNotificationRecord.query_by_rev_reg_id(
            session, event.payload["rev_reg_id"]
        )

    # Delete
    async with profile.transaction() as txn:
        for notification in notifications:
            await notification.delete_record(txn)
        await txn.commit()
