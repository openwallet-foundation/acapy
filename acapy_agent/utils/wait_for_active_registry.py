"""Utility method for waiting for active revocation registry."""

import asyncio
import logging

from ..core.profile import Profile
from ..indy.util import REVOCATION_REGISTRY_CREATION_TIMEOUT
from ..revocation.models.issuer_rev_reg_record import IssuerRevRegRecord

LOGGER = logging.getLogger(__name__)


async def wait_for_active_revocation_registry(profile: Profile, cred_def_id: str) -> None:
    """Wait for revocation registry setup to complete.

    Polls for the creation of revocation registry definitions until we have
    the 2 active registries or timeout occurs.

    Args:
        profile: The profile
        cred_def_id: The credential definition ID

    Raises:
        TimeoutError: If timeout occurs before completion

    """
    LOGGER.debug(
        "Waiting for revocation setup completion for cred_def_id: %s", cred_def_id
    )

    expected_count = 2  # Active registry
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

    raise TimeoutError(
        "Timeout waiting for revocation setup completion for credential definition "
        f"{cred_def_id}. Expected {expected_count} active revocation registries, but "
        f"{current_count} were active within {REVOCATION_REGISTRY_CREATION_TIMEOUT} "
        "seconds. Note: Revocation registry creation may still be in progress in the "
        "background. You can check status using the revocation registry endpoints."
    )
