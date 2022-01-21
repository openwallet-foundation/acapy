"""Ledger utilities."""

import re

from ..core.profile import Profile


TAA_ACCEPTED_RECORD_TYPE = "taa_accepted"

DID_EVENT_PREFIX = "acapy::REGISTER_DID::"
EVENT_LISTENER_PATTERN = re.compile(f"^{DID_EVENT_PREFIX}(.*)?$")


async def notify_register_did_event(profile: Profile, did: str, meta_data: dict):
    """Send notification for a DID post-process event."""
    await profile.notify(
        DID_EVENT_PREFIX + did,
        meta_data,
    )
