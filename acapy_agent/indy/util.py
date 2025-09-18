"""Utilities for dealing with Indy conventions."""

import asyncio
import logging
import os
from os import getenv, makedirs, urandom
from os.path import isdir, join
from pathlib import Path
from platform import system
from typing import Optional

from ..core.profile import Profile
from ..revocation.models.issuer_rev_reg_record import IssuerRevRegRecord
from .issuer import IndyIssuerError

LOGGER = logging.getLogger(__name__)

REVOCATION_REGISTRY_CREATION_TIMEOUT = float(
    os.getenv("REVOCATION_REGISTRY_CREATION_TIMEOUT", "120.0")
)


async def generate_pr_nonce() -> str:
    """Generate a nonce for a proof request."""
    # equivalent to indy.anoncreds.generate_nonce
    return str(int.from_bytes(urandom(10), "big"))


def indy_client_dir(subpath: Optional[str] = None, create: bool = False) -> str:
    """Return '/'-terminated subdirectory of indy-client directory.

    Args:
        subpath: subpath within indy-client structure
        create: whether to create subdirectory if absent

    """
    home = Path.home()
    target_dir = join(
        home,
        (
            "Documents"
            if isdir(join(home, "Documents"))
            else getenv("EXTERNAL_STORAGE", "")
            if system() == "Linux"
            else ""
        ),
        ".indy_client",
        subpath if subpath else "",
        "",  # set trailing separator
    )
    if create:
        makedirs(target_dir, exist_ok=True)

    return target_dir


async def wait_for_active_revocation_registry(profile: Profile, cred_def_id: str) -> None:
    """Wait for revocation registry setup to complete.

    Polls for the creation of revocation registry definitions until we have
    the 1 active registry or timeout occurs.

    Args:
        profile: The profile
        cred_def_id: The credential definition ID

    Raises:
        IndyIssuerError: If timeout occurs before completion
    """
    LOGGER.debug(
        "Waiting for revocation setup completion for cred_def_id: %s", cred_def_id
    )

    expected_count = 1  # Active registry
    poll_interval = 0.5  # Poll every 500ms
    max_iterations = int(REVOCATION_REGISTRY_CREATION_TIMEOUT / poll_interval)
    registries = []

    for _iteration in range(max_iterations):
        try:
            # Check for finished revocation registry definitions
            async with profile.session() as session:
                registries = await IssuerRevRegRecord.query_by_cred_def_id(
                    session, cred_def_id, IssuerRevRegRecord.STATE_ACTIVE
                )

            current_count = len(registries)
            LOGGER.debug(
                "Revocation setup progress for %s: %d registries active",
                cred_def_id,
                current_count,
            )

            if current_count >= expected_count:
                LOGGER.info(
                    "Revocation setup completed for cred_def_id: %s "
                    "(%d registries created)",
                    cred_def_id,
                    current_count,
                )
                return

        except Exception as e:
            LOGGER.warning(
                "Error checking revocation setup progress for %s: %s", cred_def_id, e
            )
            # Continue polling despite errors - they might be transient

        await asyncio.sleep(poll_interval)  # Wait before next poll

    # Timeout occurred
    current_count = len(registries)

    raise IndyIssuerError(
        "Timeout waiting for revocation setup completion for credential definition "
        f"{cred_def_id}. Expected 1 active revocation registries, but none "
        f"were active within {REVOCATION_REGISTRY_CREATION_TIMEOUT} seconds. "
        "Note: Revocation registry creation may still be in progress in the "
        "background. You can check status using the revocation registry endpoints."
    )
