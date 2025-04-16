"""Recover a revocation registry."""

import hashlib
import logging
import time

import aiohttp
import base58
import indy_vdr
from anoncreds import RevocationRegistry, RevocationRegistryDefinition

from ...models.revocation import RevList

LOGGER = logging.getLogger(__name__)


"""
This module calculates a new ledger accumulator, based on the revocation status
on the ledger vs revocations recorded in the wallet.
The calculated transaction can be written to the ledger to get the ledger back
in sync with the wallet.
This function can be used if there were previous revocation errors (i.e. the
credential revocation was successfully written to the wallet but the ledger write
failed.)
"""


class RevocRecoveryException(Exception):
    """Raise exception generating the recovery transaction."""


async def _check_tails_hash_for_inconsistency(tails_location: str, tails_hash: str):
    async with aiohttp.ClientSession() as session:
        LOGGER.debug("Tails URL: %s", tails_location)
        tails_data_http_response = await session.get(tails_location)
        tails_data = await tails_data_http_response.read()
        remote_tails_hash = base58.b58encode(hashlib.sha256(tails_data).digest()).decode(
            "utf-8"
        )
        if remote_tails_hash != tails_hash:
            raise RevocRecoveryException(
                f"Tails hash mismatch {remote_tails_hash} {tails_hash}"
            )
        else:
            LOGGER.debug(f"Checked tails hash: {tails_hash}")


async def fetch_txns(
    genesis_txns: str, registry_id: str, issuer_id: str
) -> tuple[
    dict,
    set[int],
]:
    """Fetch tails file and revocation registry information."""

    LOGGER.debug(f"Fetch revocation registry def {registry_id} from ledger")
    revoc_reg_delta_request = indy_vdr.ledger.build_get_revoc_reg_def_request(
        None, registry_id
    )

    pool = await indy_vdr.open_pool(transactions=genesis_txns)
    result = await pool.submit_request(revoc_reg_delta_request)
    if not result["data"]:
        raise RevocRecoveryException(f"Registry definition not found for {registry_id}")

    # Load the anoncreds revocation registry definition
    rev_reg_def_raw = result["data"]
    rev_reg_def_raw["ver"] = "1.0"
    rev_reg_def_raw["issuerId"] = issuer_id
    revoc_reg_def = RevocationRegistryDefinition.load(rev_reg_def_raw)

    await _check_tails_hash_for_inconsistency(
        revoc_reg_def.tails_location, revoc_reg_def.tails_hash
    )

    LOGGER.debug(f"Fetch revocation registry delta {registry_id} from ledger")
    to_timestamp = int(time.time())
    revoc_reg_delta_request = indy_vdr.ledger.build_get_revoc_reg_delta_request(
        None, registry_id, None, to_timestamp
    )
    result = await pool.submit_request(revoc_reg_delta_request)
    if not result["data"]:
        raise RevocRecoveryException("Error fetching delta from ledger")

    registry_from_ledger = result["data"]["value"]["accum_to"]
    registry_from_ledger["ver"] = "1.0"
    revoked = set(result["data"]["value"]["revoked"])
    LOGGER.debug("Ledger revoked indexes: %s", revoked)

    return registry_from_ledger, revoked


async def generate_ledger_rrrecovery_txn(genesis_txns: str, rev_list: RevList) -> dict:
    """Generate a new ledger accum entry, using the wallet value if revocations ahead of ledger."""  # noqa: E501

    registry_from_ledger, prev_revoked = await fetch_txns(
        genesis_txns, rev_list.rev_reg_def_id, rev_list.issuer_id
    )

    set_revoked = {
        index for index, value in enumerate(rev_list.revocation_list) if value == 1
    }
    mismatch = prev_revoked - set_revoked
    if mismatch:
        LOGGER.warning(
            "Credential index(es) revoked on the ledger, but not in wallet: %s",
            mismatch,
        )

    updates = set_revoked - prev_revoked
    if not updates:
        LOGGER.debug("No updates to perform")
        return {}
    else:
        LOGGER.debug("New revoked indexes: %s", updates)

        # Prepare the transaction to write to the ledger
        registry = RevocationRegistry.load(registry_from_ledger)
        registry = registry.to_dict()
        registry["ver"] = "1.0"
        registry["value"]["prevAccum"] = registry_from_ledger["value"]["accum"]
        registry["value"]["accum"] = rev_list.current_accumulator
        registry["value"]["issued"] = []
        registry["value"]["revoked"] = list(updates)
    return registry
