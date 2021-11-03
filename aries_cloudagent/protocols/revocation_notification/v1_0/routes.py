"""Routes for revocation notification."""
import logging
import re
from typing import cast

from ....core.event_bus import Event, EventBus
from ....core.profile import Profile
from ....messaging.responder import BaseResponder
from ....revocation.models.issuer_cred_rev_record import IssuerCredRevRecord
from ....revocation.util import REVOCATION_PUBLISHED_EVENT, REVOCATION_EVENT_PREFIX
from ....storage.error import StorageError, StorageNotFoundError
from .models.rev_notification_record import RevNotificationRecord

LOGGER = logging.getLogger(__name__)


def register_events(event_bus: EventBus):
    event_bus.subscribe(
        re.compile(f"^{REVOCATION_EVENT_PREFIX}{REVOCATION_PUBLISHED_EVENT}.*"),
        on_issuer_revoke_event,
    )


async def on_issuer_revoke_event(profile: Profile, event: Event):
    """Handle issuer revoke event."""
    if not profile.settings.get("revocation.notify"):
        return

    LOGGER.debug("Sending notification of revocation to recipient: %s", event.payload)

    cred_rev_rec = IssuerCredRevRecord.deserialize(event.payload)
    cred_rev_rec = cast(IssuerCredRevRecord, cred_rev_rec)
    try:
        async with profile.session() as session:
            rev_notify_rec = await RevNotificationRecord.query_by_ids(
                session,
                rev_reg_id=cred_rev_rec.rev_reg_id,
                cred_rev_id=cred_rev_rec.cred_rev_id,
            )
        notification = rev_notify_rec.to_message()
        responder = profile.inject(BaseResponder)
        await responder.send(notification, connection_id=rev_notify_rec.connection_id)
    except StorageNotFoundError:
        LOGGER.info(
            "No revocation notification record found for revoked credential; "
            "no notification will be sent"
        )
    except StorageError:
        LOGGER.exception("Failed to retrieve revocation notification record")
