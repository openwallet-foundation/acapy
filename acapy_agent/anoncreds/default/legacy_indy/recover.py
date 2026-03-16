"""Recover a revocation registry."""

import asyncio
import hashlib
import logging
import time
from typing import Optional, Sequence, Tuple

import aiohttp
import base58
import indy_vdr
from anoncreds import (
    RevocationRegistry,
    RevocationRegistryDefinition,
)
from uuid_utils import uuid4

from ....cache.base import BaseCache
from ....connections.models.conn_record import ConnRecord
from ....core.profile import Profile
from ....ledger.base import BaseLedger
from ....ledger.error import (
    LedgerError,
)
from ....ledger.multiple_ledger.ledger_requests_executor import (
    GET_REVOC_REG_DELTA,
    IndyLedgerRequestsExecutor,
)
from ....messaging.responder import BaseResponder
from ....multitenant.base import BaseMultitenantManager
from ....protocols.endorse_transaction.v1_0.manager import (
    TransactionManager,
    TransactionManagerError,
)
from ....protocols.endorse_transaction.v1_0.util import get_endorser_connection_id
from ....storage.error import StorageError
from ...constants import (
    CATEGORY_REV_LIST,
    CATEGORY_REV_REG_DEF,
)
from ...models.issuer_cred_rev_record import IssuerCredRevRecord
from ...models.revocation import (
    RevList,
)
from ...revocation.manager import RevocationManagerError

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


async def generate_ledger_rrrecovery_txn(genesis_txns: str, rev_list: RevList):
    """Generate a new ledger accum entry, based on wallet vs ledger revocation state."""
    new_delta = None

    ledger_data = await fetch_txns(
        genesis_txns, rev_list.rev_reg_def_id, rev_list.issuer_id
    )
    if not ledger_data:
        return new_delta
    registry_from_ledger, prev_revoked = ledger_data

    set_revoked = {
        i for i, revoked in enumerate(rev_list.revocation_list) if revoked == 1
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


async def _get_endorser_info(
    profile: Profile,
) -> Tuple[Optional[str], Optional[ConnRecord]]:
    connection_id = await get_endorser_connection_id(profile)

    endorser_did = None
    async with profile.session() as session:
        connection_record = await ConnRecord.retrieve_by_id(session, connection_id)
        endorser_info = await connection_record.metadata_get(session, "endorser_info")
    endorser_did = endorser_info.get("endorser_did")

    return endorser_did, connection_record


async def fix_and_publish_from_invalid_accum_err(profile: Profile, err_msg: str):
    """Fix and publish revocation registry entries from invalid accumulator error."""
    cache = profile.inject_or(BaseCache)

    async def check_retry(accum):
        """Used to manage retries for fixing revocation registry entries."""
        if cache is None:
            LOGGER.warning(
                "No cache backend configured; skipping retry tracking for %s",
                accum,
            )
            return

        retry_value = await cache.get(accum)
        if not retry_value:
            await cache.set(accum, 5)
        else:
            if retry_value > 0:
                await cache.set(accum, retry_value - 1)
            else:
                LOGGER.error(
                    "Revocation registry entry transaction failed for %s",
                    accum,
                )

    def get_genesis_transactions():
        """Get the genesis transactions needed for fixing broken accum."""
        genesis_transactions = profile.context.settings.get("ledger.genesis_transactions")
        if not genesis_transactions:
            write_ledger = profile.context.injector.inject(BaseLedger)
            pool = write_ledger.pool
            genesis_transactions = pool.genesis_txns
        return genesis_transactions

    async def create_and_send_endorser_txn():
        """Create and send the endorser transaction again."""
        async with ledger:
            # Create the revocation registry entry
            (rev_reg_def_id, requested_txn) = await ledger.send_revoc_reg_entry(
                rev_list.rev_reg_def_id,
                "CL_ACCUM",
                recovery_txn,
                rev_list.issuer_id,
                write_ledger=False,
                endorser_did=endorser_did,
            )

        job_id = uuid4().hex
        meta_data = {
            "context": {
                "job_id": job_id,
                "rev_reg_def_id": rev_reg_def_id,
                "rev_list": rev_list.serialize(),
                "options": {
                    "endorser_connection_id": connection.connection_id,
                    "create_transaction_for_endorser": True,
                },
            }
        }

        # Send the transaction to the endorser again with recovery txn
        transaction_manager = TransactionManager(profile)
        try:
            revo_transaction = await transaction_manager.create_record(
                messages_attach=requested_txn["signed_txn"],
                connection_id=connection.connection_id,
                meta_data=meta_data,
            )
            (
                revo_transaction,
                revo_transaction_request,
            ) = await transaction_manager.create_request(transaction=revo_transaction)
        except (StorageError, TransactionManagerError) as err:
            raise RevocationManagerError(err.roll_up) from err

        responder = profile.inject_or(BaseResponder)
        if not responder:
            raise RevocationManagerError(
                "No responder found. Unable to send transaction request"
            )
        await responder.send(
            revo_transaction_request,
            connection_id=connection.connection_id,
        )

    async with profile.session() as session:
        rev_reg_records = await session.handle.fetch_all(
            CATEGORY_REV_REG_DEF,
            {},
        )
        # Cycle through all rev_rev_def records to find the offending accumulator
        for rev_reg_entry in rev_reg_records:
            ledger = session.inject_or(BaseLedger)
            async with ledger:
                # Get the value from the ledger
                (accum_response, _) = await ledger.get_revoc_reg_delta(rev_reg_entry.name)
                accum = accum_response.get("value", {}).get("accum")

            # If the accum from the ledger matches the error message, fix it
            if accum and accum in err_msg:
                # if accum and accum in err_msg:
                await check_retry(accum)

                # Get the genesis transactions needed for fix
                genesis_transactions = get_genesis_transactions()

                # We know this needs endorsement
                endorser_did, connection = await _get_endorser_info(profile)
                rev_list_entry = await session.handle.fetch(
                    CATEGORY_REV_LIST, rev_reg_entry.name
                )

                rev_list = RevList.deserialize(rev_list_entry.value_json["rev_list"])

                (
                    rev_reg_delta,
                    recovery_txn,
                    applied_txn,
                ) = await fix_ledger_entry(
                    profile, rev_list, False, genesis_transactions, False, endorser_did
                )
                if recovery_txn.get("value"):
                    await create_and_send_endorser_txn()

                # Some time in between re-tries
                await asyncio.sleep(1)


def _get_revoked_discrepancies(
    recs: Sequence[IssuerCredRevRecord], rev_reg_delta: dict
) -> Tuple[list, int]:
    revoked_ids = []
    rec_count = 0
    for rec in recs:
        if rec.state == IssuerCredRevRecord.STATE_REVOKED:
            revoked_ids.append(int(rec.cred_rev_id))
            if int(rec.cred_rev_id) not in rev_reg_delta["value"]["revoked"]:
                rec_count += 1

    return revoked_ids, rec_count


async def fix_ledger_entry(
    profile: Profile,
    rev_list: RevList,
    apply_ledger_update: bool,
    genesis_transactions: str,
    write_ledger: bool = True,
    endorser_did: Optional[str] = None,
) -> Tuple[dict, dict, dict]:
    """Fix the ledger entry to match wallet-recorded credentials."""
    applied_txn = {}
    recovery_txn = {}

    LOGGER.debug("Fixing ledger entry for revocation list...")

    multitenant_mgr = profile.inject_or(BaseMultitenantManager)
    if multitenant_mgr:
        ledger_exec_inst = IndyLedgerRequestsExecutor(profile)
    else:
        ledger_exec_inst = profile.inject(IndyLedgerRequestsExecutor)
    _, ledger = await ledger_exec_inst.get_ledger_for_identifier(
        rev_list.rev_reg_def_id,
        txn_record_type=GET_REVOC_REG_DELTA,
    )

    if not ledger:
        reason = "No ledger available for revocation registry entry fix"
        if not profile.context.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise LedgerError(reason=reason)

    async with ledger:
        (rev_reg_delta, _) = await ledger.get_revoc_reg_delta(rev_list.rev_reg_def_id)

        async with profile.session() as session:
            # get rev reg records from wallet (revocations and status)
            recs = await IssuerCredRevRecord.query_by_ids(
                session, rev_reg_id=rev_list.rev_reg_def_id
            )

            revoked_ids, rec_count = _get_revoked_discrepancies(recs, rev_reg_delta)

            LOGGER.debug(f"Fixed entry recs count = {rec_count}")
            LOGGER.debug(f"Fixed entry recs revoked ids = {revoked_ids}")

            # No update required if no discrepancies
            if rec_count == 0:
                return (rev_reg_delta, {}, {})

            # We have revocation discrepancies, generate the recovery txn
            recovery_txn = await generate_ledger_rrrecovery_txn(
                genesis_transactions, rev_list
            )

            # If no recovery transaction was generated, skip ledger update
            if not recovery_txn:
                LOGGER.debug(
                    "No recovery transaction generated for revocation list %s; "
                    "skipping ledger update",
                    rev_list.rev_reg_def_id,
                )
                return (rev_reg_delta, recovery_txn, applied_txn)

            if apply_ledger_update:
                ledger_response = await ledger.send_revoc_reg_entry(
                    rev_list.rev_reg_def_id,
                    "CL_ACCUM",
                    recovery_txn,
                    rev_list.issuer_id,
                    write_ledger=write_ledger,
                    endorser_did=endorser_did,
                )

                if isinstance(ledger_response, dict) and "result" in ledger_response:
                    applied_txn = ledger_response["result"]

                    # Update the local wallets rev reg entry with the new accumulator value
                    rev_list_value_json = rev_list.value_json
                    rev_list_value_json["rev_list"]["currentAccumulator"] = applied_txn[
                        "txn"
                    ]["data"]["value"]["accum"]
                    rev_list.current_accumulator = applied_txn["txn"]["data"]["value"][
                        "accum"
                    ]
                    await session.handle.replace(
                        CATEGORY_REV_LIST,
                        rev_list.rev_reg_def_id,
                        rev_list_value_json,
                        rev_list.tags,
                    )
                    return (rev_reg_delta, recovery_txn, applied_txn)

    # Ledger update not applied, return without applied_txn
    return (rev_reg_delta, recovery_txn, {})
