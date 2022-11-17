"""Revocation utilities."""

import re
from typing import Sequence

from ..core.profile import Profile


REVOCATION_EVENT_PREFIX = "acapy::REVOCATION::"
EVENT_LISTENER_PATTERN = re.compile(f"^{REVOCATION_EVENT_PREFIX}(.*)?$")
REVOCATION_REG_INIT_EVENT = "REGISTRY_INIT"
REVOCATION_REG_ENDORSED_EVENT = "REGISTRY_ENDORSED"
REVOCATION_ENTRY_ENDORSED_EVENT = "ENTRY_ENDORSED"
REVOCATION_ENTRY_EVENT = "SEND_ENTRY"
REVOCATION_PUBLISHED_EVENT = "published"
REVOCATION_CLEAR_PENDING_EVENT = "clear-pending"


async def notify_revocation_reg_init_event(
    profile: Profile,
    issuer_rev_id: str,
    create_pending_rev_reg: bool = False,
    endorser_connection_id: str = None,
):
    """Send notification for a revocation registry init event."""
    meta_data = {
        "context": {
            "issuer_rev_id": issuer_rev_id,
        },
        "processing": {"create_pending_rev_reg": create_pending_rev_reg},
    }
    if endorser_connection_id:
        meta_data["endorser"] = {"connection_id": endorser_connection_id}
    topic = f"{REVOCATION_EVENT_PREFIX}{REVOCATION_REG_INIT_EVENT}::{issuer_rev_id}"
    await profile.notify(topic, meta_data)


async def notify_revocation_entry_event(
    profile: Profile, issuer_rev_id: str, meta_data: dict
):
    """Send notification for a revocation registry entry event."""
    topic = f"{REVOCATION_EVENT_PREFIX}{REVOCATION_ENTRY_EVENT}::{issuer_rev_id}"
    await profile.notify(topic, meta_data)


async def notify_revocation_reg_endorsed_event(
    profile: Profile, rev_reg_id: str, meta_data: dict
):
    """Send notification for a revocation registry endorsement event."""
    topic = f"{REVOCATION_EVENT_PREFIX}{REVOCATION_REG_ENDORSED_EVENT}::{rev_reg_id}"
    await profile.notify(topic, meta_data)


async def notify_revocation_entry_endorsed_event(
    profile: Profile, rev_reg_id: str, meta_data: dict
):
    """Send notification for a revocation registry entry endorsement event."""
    topic = f"{REVOCATION_EVENT_PREFIX}{REVOCATION_ENTRY_ENDORSED_EVENT}::{rev_reg_id}"
    await profile.notify(topic, meta_data)


async def notify_revocation_published_event(
    profile: Profile,
    rev_reg_id: str,
    crids: Sequence[str],
):
    """Send notification of credential revoked as issuer."""
    topic = f"{REVOCATION_EVENT_PREFIX}{REVOCATION_PUBLISHED_EVENT}::{rev_reg_id}"
    await profile.notify(topic, {"rev_reg_id": rev_reg_id, "crids": crids})


async def notify_pending_cleared_event(
    profile: Profile,
    rev_reg_id: str,
):
    """Send notification of credential revoked as issuer."""
    topic = f"{REVOCATION_EVENT_PREFIX}{REVOCATION_CLEAR_PENDING_EVENT}::{rev_reg_id}"
    await profile.notify(topic, {"rev_reg_id": rev_reg_id})
