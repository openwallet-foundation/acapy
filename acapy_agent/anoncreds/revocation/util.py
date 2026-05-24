from typing import Sequence

from acapy_agent.core.profile import Profile

REVOCATION_EVENT_PREFIX = "acapy::REVOCATION::"
REVOCATION_CLEAR_PENDING_EVENT = "clear-pending"
REVOCATION_PUBLISHED_EVENT = "published"


async def notify_pending_cleared_event(
    profile: Profile,
    rev_reg_id: str,
):
    """Send notification of credential revoked as issuer."""
    topic = f"{REVOCATION_EVENT_PREFIX}{REVOCATION_CLEAR_PENDING_EVENT}::{rev_reg_id}"
    await profile.notify(topic, {"rev_reg_id": rev_reg_id})


async def notify_revocation_published_event(
    profile: Profile,
    rev_reg_id: str,
    crids: Sequence[str],
):
    """Send notification of credential revoked as issuer."""
    topic = f"{REVOCATION_EVENT_PREFIX}{REVOCATION_PUBLISHED_EVENT}::{rev_reg_id}"
    await profile.notify(topic, {"rev_reg_id": rev_reg_id, "crids": crids})
