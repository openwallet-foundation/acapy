"""Revocation utilities."""

import re
from typing import Sequence

from ..core.profile import Profile
from ..protocols.endorse_transaction.v1_0.util import (
    get_endorser_connection_id,
    is_author_role,
)


REVOCATION_EVENT_PREFIX = "acapy::REVOCATION::"
EVENT_LISTENER_PATTERN = re.compile(f"^{REVOCATION_EVENT_PREFIX}(.*)?$")
REVOCATION_REG_EVENT = "REGISTRY"
REVOCATION_ENTRY_EVENT = "ENTRY"
REVOCATION_TAILS_EVENT = "TAILS"
REVOCATION_PUBLISHED_EVENT = "published"
REVOCATION_CLEAR_PENDING_EVENT = "clear-pending"


async def notify_revocation_reg_event(
    profile: Profile,
    cred_def_id: str,
    rev_reg_size: int,
    auto_create_rev_reg: bool = False,
    create_pending_rev_reg: bool = False,
    endorser_connection_id: str = None,
):
    """Send notification for a revocation registry event."""
    meta_data = {
        "context": {
            "cred_def_id": cred_def_id,
            "support_revocation": True,
            "rev_reg_size": rev_reg_size,
        },
        "processing": {
            "auto_create_rev_reg": auto_create_rev_reg,
        },
    }
    if (
        (not endorser_connection_id)
        and is_author_role(profile)
        and "endorser" not in meta_data
    ):
        endorser_connection_id = await get_endorser_connection_id(profile)
        if not endorser_connection_id:
            raise Exception(reason="No endorser connection found")
    if create_pending_rev_reg:
        meta_data["processing"]["create_pending_rev_reg"] = create_pending_rev_reg
    if endorser_connection_id:
        meta_data["endorser"] = {"connection_id": endorser_connection_id}
    event_id = REVOCATION_EVENT_PREFIX + REVOCATION_REG_EVENT + "::" + cred_def_id
    await profile.notify(
        event_id,
        meta_data,
    )


async def notify_revocation_entry_event(
    profile: Profile, rev_reg_id: str, meta_data: dict
):
    """Send notification for a revocation registry event."""
    event_id = REVOCATION_EVENT_PREFIX + REVOCATION_ENTRY_EVENT + "::" + rev_reg_id
    await profile.notify(
        event_id,
        meta_data,
    )


async def notify_revocation_tails_file_event(
    profile: Profile, rev_reg_id: str, meta_data: dict
):
    """Send notification for a revocation tails file event."""
    event_id = REVOCATION_EVENT_PREFIX + REVOCATION_TAILS_EVENT + "::" + rev_reg_id
    await profile.notify(
        event_id,
        meta_data,
    )


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
