"""Recover a revocation registry."""

import hashlib
import importlib
import logging
import tempfile
import time

import aiohttp
import base58


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


async def fetch_txns(genesis_txns, registry_id):
    """Fetch tails file and revocation registry information."""

    try:
        vdr_module = importlib.import_module("indy_vdr")
        credx_module = importlib.import_module("indy_credx")
    except Exception as e:
        raise RevocRecoveryException(f"Failed to import library {e}")

    pool = await vdr_module.open_pool(transactions=genesis_txns)
    LOGGER.debug("Connected to pool")

    LOGGER.debug("Fetch registry: %s", registry_id)
    fetch = vdr_module.ledger.build_get_revoc_reg_def_request(None, registry_id)
    result = await pool.submit_request(fetch)
    if not result["data"]:
        raise RevocRecoveryException(f"Registry definition not found for {registry_id}")
    data = result["data"]
    data["ver"] = "1.0"
    defn = credx_module.RevocationRegistryDefinition.load(data)
    LOGGER.debug("Tails URL: %s", defn.tails_location)

    async with aiohttp.ClientSession() as session:
        data = await session.get(defn.tails_location)
        tails_data = await data.read()
        tails_hash = base58.b58encode(hashlib.sha256(tails_data).digest()).decode(
            "utf-8"
        )
        if tails_hash != defn.tails_hash:
            raise RevocRecoveryException(
                f"Tails hash mismatch {tails_hash} {defn.tails_hash}"
            )
        else:
            LOGGER.debug("Checked tails hash: %s", tails_hash)
        tails_temp = tempfile.NamedTemporaryFile(delete=False)
        tails_temp.write(tails_data)
        tails_temp.close()

    to_timestamp = int(time.time())
    fetch = vdr_module.ledger.build_get_revoc_reg_delta_request(
        None, registry_id, None, to_timestamp
    )
    result = await pool.submit_request(fetch)
    if not result["data"]:
        raise RevocRecoveryException("Error fetching delta from ledger")

    accum_to = result["data"]["value"]["accum_to"]
    accum_to["ver"] = "1.0"
    delta = credx_module.RevocationRegistryDelta.load(accum_to)
    registry = credx_module.RevocationRegistry.load(accum_to)
    LOGGER.debug("Ledger registry state: %s", registry.to_json())
    revoked = set(result["data"]["value"]["revoked"])
    LOGGER.debug("Ledger revoked indexes: %s", revoked)

    return defn, registry, delta, revoked, tails_temp


async def generate_ledger_rrrecovery_txn(
    genesis_txns, registry_id, set_revoked, cred_def, rev_reg_def_private
):
    """Generate a new ledger accum entry, based on wallet vs ledger revocation state."""

    new_delta = None

    ledger_data = await fetch_txns(genesis_txns, registry_id)
    if not ledger_data:
        return new_delta
    defn, registry, delta, prev_revoked, tails_temp = ledger_data

    set_revoked = set(set_revoked)
    mismatch = prev_revoked - set_revoked
    if mismatch:
        LOGGER.warn(
            "Credential index(es) revoked on the ledger, but not in wallet: %s",
            mismatch,
        )

    updates = set_revoked - prev_revoked
    if not updates:
        LOGGER.debug("No updates to perform")
    else:
        LOGGER.debug("New revoked indexes: %s", updates)

        LOGGER.debug("tails_temp: %s", tails_temp.name)
        update_registry = registry.copy()
        new_delta = update_registry.update(
            cred_def, defn, rev_reg_def_private, [], updates
        )

        LOGGER.debug("New delta:")
        LOGGER.debug(new_delta.to_json())

    return new_delta
