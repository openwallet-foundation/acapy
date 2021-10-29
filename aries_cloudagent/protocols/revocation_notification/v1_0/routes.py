"""Routes for revocation notification."""
import logging
import re

from ....messaging.responder import BaseResponder
from ....core.event_bus import Event, EventBus
from ....core.profile import Profile

from ....revocation.models.issuer_cred_rev_record import IssuerCredRevRecord
from ....revocation.util import (
    ISSUER_REVOKE_EVENT,
    REVOCATION_EVENT_PREFIX,
)
from .messages.revoke import Revoke

LOGGER = logging.getLogger(__name__)


def register_events(event_bus: EventBus):
    event_bus.subscribe(
        re.compile(f"^{REVOCATION_EVENT_PREFIX}{ISSUER_REVOKE_EVENT}.*"),
        on_issuer_revoke_event,
    )


async def on_issuer_revoke_event(profile: Profile, event: Event):
    """Handle issuer revoke event."""
    if not profile.settings.get("revocation.notify"):
        return

    LOGGER.debug("Sending notification of revocation to recipient: %s", event.payload)

    cred_rev_rec = IssuerCredRevRecord.deserialize(event.payload)
    notification = Revoke(thread_id=cred_rev_rec.thread_id)

    responder = profile.inject(BaseResponder)
    await responder.send(notification, connection_id=cred_rev_rec.connection_id)
