"""Recover a revocation registry."""

import asyncio
import hashlib
import logging
import time
from typing import Optional, Sequence, Tuple

from ....revocation_anoncreds.models.issuer_cred_rev_record import IssuerCredRevRecord

from ...events import RevListFinishedEvent, RevListFinishedPayload

from ....indy.credx.issuer import CATEGORY_REV_REG_DEF

from ....revocation_anoncreds.manager import RevocationManagerError

from ...revocation import CATEGORY_REV_LIST

from ...models.revocation import RevList
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


async def _check_tails_hash_for_inconsistency(
    tails_location: str, tails_hash: str
) -> None:
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


async def fetch_transaction_and_revoked_credentials_from_ledger(
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
    if not result.get("data"):
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
    if not result.get("data"):
        raise RevocRecoveryException("Error fetching delta from ledger")

    registry_from_ledger = result["data"]["value"]["accum_to"]
    registry_from_ledger["ver"] = "1.0"
    revoked = set(result["data"]["value"]["revoked"])
    LOGGER.debug("Ledger revoked indexes: %s", revoked)

    return registry_from_ledger, revoked


async def generate_ledger_revocation_registry_recovery_txn(
    genesis_txns: str, rev_list: RevList
) -> dict:
    """Generate a new ledger accum entry, based on wallet vs ledger revocation state."""
    ledger_data = await fetch_transaction_and_revoked_credentials_from_ledger(
        genesis_txns, rev_list.rev_reg_def_id, rev_list.issuer_id
    )
    if not ledger_data:
        return {}

    registry_from_ledger, prev_revoked = ledger_data

    # Create a set of revoked indexes from the revocation list to match against the
    # ledger revoked indexes
    set_revoked = {
        i for i, revoked in enumerate(rev_list.revocation_list) if revoked == 1
    }
    mismatch = prev_revoked - set_revoked
    if mismatch:
        # Somehow we have revoked credentials in the ledger that are not revoked in the
        # wallet. This shouldn't happen except perhaps with the 0 index which is reserved
        # by the indy algorithm and not used for actual credentials.
        # Log a warning but continue with the fix.
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

    if connection_id is None:
        return None, None

    endorser_did = None
    async with profile.session() as session:
        connection_record = await ConnRecord.retrieve_by_id(session, connection_id)
        endorser_info = await connection_record.metadata_get(session, "endorser_info")
        endorser_did = endorser_info.get("endorser_did")

    return endorser_did, connection_record


async def _track_retry(cache: BaseCache, accum: str) -> None:
    """Tracks retry for 5 attempts for accum value. This is hardcoded to avoid infinite retries."""  # noqa: E501
    if not cache:
        LOGGER.warning(
            "No cache backend configured; skipping retry tracking for %s",
            accum,
        )
        return

    retry_value = await cache.get(accum)

    if retry_value is None:
        await cache.set(accum, 5)
        return

    if retry_value > 0:
        await cache.set(accum, retry_value - 1)
    else:
        LOGGER.error(
            "Revocation registry entry transaction failed for %s",
            accum,
        )


async def _get_ledger_accumulator(ledger: BaseLedger, rev_reg_id: str):
    async with ledger:
        accum_response, _ = await ledger.get_revoc_reg_delta(rev_reg_id)

    return accum_response.get("value", {}).get("accum")


def _get_genesis_transactions(profile: Profile):
    genesis = profile.context.settings.get("ledger.genesis_transactions")

    if genesis:
        return genesis

    ledger = profile.context.injector.inject(BaseLedger)
    return ledger.pool.genesis_txns


async def _get_rev_list(session, rev_reg_id: str) -> RevList:
    rev_list_entry = await session.handle.fetch(CATEGORY_REV_LIST, rev_reg_id)
    return RevList.deserialize(rev_list_entry.value_json["rev_list"])


async def _send_txn(
    profile: Profile,
    ledger: BaseLedger,
    rev_list: RevList,
    recovery_txn: dict,
    endorser_did: str,
    connection: ConnRecord,
) -> None:
    async with ledger:
        result = await ledger.send_revoc_reg_entry(
            rev_list.rev_reg_def_id,
            "CL_ACCUM",
            recovery_txn,
            rev_list.issuer_id,
            write_ledger=True if not endorser_did else False,
            endorser_did=endorser_did,
        )

    # Requires the endorser sends the transaction to the ledger, Otherwise self
    # endorsed and sent to ledger above.
    if endorser_did:
        (rev_reg_def_id, requested_txn) = result

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

        transaction_manager = TransactionManager(profile)

        try:
            txn = await transaction_manager.create_record(
                messages_attach=requested_txn["signed_txn"],
                connection_id=connection.connection_id,
                meta_data=meta_data,
            )

            txn, txn_request = await transaction_manager.create_request(transaction=txn)

        except (StorageError, TransactionManagerError) as err:
            raise RevocationManagerError(err.roll_up) from err

        responder = profile.inject_or(BaseResponder)

        if not responder:
            raise RevocationManagerError(
                "No responder found. Unable to send transaction request"
            )

        await responder.send(txn_request, connection_id=connection.connection_id)


async def fix_and_publish_from_invalid_accum_err(profile: Profile, err_msg: str):
    """Fix and publish revocation registry entries from invalid accumulator error."""
    cache = profile.inject_or(BaseCache)

    async with profile.session() as session:
        rev_reg_records = await session.handle.fetch_all(CATEGORY_REV_REG_DEF, {})

        # We have no way to know which revocation registry entry the invalid accumulator
        # error is related to, so we need to check each of them for the accumulator value
        # and retry if it matches the error message.
        for rev_reg_entry in rev_reg_records:
            ledger = session.inject_or(BaseLedger)

            accum = await _get_ledger_accumulator(ledger, rev_reg_entry.name)

            if not accum or accum not in err_msg:
                continue

            # Retry for a finite number of times or until the accumulator is
            # no longer in the error message
            await _track_retry(cache, accum)

            genesis_transactions = _get_genesis_transactions(profile)

            endorser_did, connection = await _get_endorser_info(profile)
            write_ledger = False if endorser_did is None else True

            rev_list = await _get_rev_list(session, rev_reg_entry.name)

            _, recovery_txn, _ = await fix_ledger_entry(
                profile,
                rev_list,
                True,
                genesis_transactions,
                write_ledger,
                endorser_did,
            )

            # Generating the recovery transaction succeeded. Send it to the ledger.
            if recovery_txn.get("value"):
                await _send_txn(
                    profile,
                    ledger,
                    rev_list,
                    recovery_txn,
                    endorser_did,
                    connection,
                )
                revoked = recovery_txn["value"]["revoked"]
                LOGGER.info(
                    "Notifying about %d revoked credentials for rev_reg_def_id: %s",
                    len(revoked),
                    rev_list.rev_reg_def_id,
                )
                await profile.notify(
                    RevListFinishedEvent.event_topic,
                    RevListFinishedPayload(rev_list.rev_reg_def_id, revoked, {}),
                )
                return

            # Wait a second before retrying for the same revocation registry. Hopefully
            # short term connection or ledger issues will be resolved by then.
            # If not, we'll retry again on the next attempted revocation for this
            # registry.
            await asyncio.sleep(1)


def _get_revoked_discrepancies(
    recs: Sequence[IssuerCredRevRecord], rev_reg_delta: dict
) -> Tuple[list, int]:
    """Get issuer revoked credential ids from wallet records and count discrepancies with ledger delta."""  # noqa: E501
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

            # We have revocation discrepancies, generate the recovery txn.
            # We're using the rev_list as source of truth instead of issuer
            # cred_rev records. These should always be in sync.
            recovery_txn = await generate_ledger_revocation_registry_recovery_txn(
                genesis_transactions, rev_list
            )

            # If no recovery transaction was generated, skip ledger update
            if not recovery_txn:
                LOGGER.debug(
                    "No recovery transaction generated for revocation list %s; "
                    "skipping ledger update",
                    rev_list.rev_reg_def_id,
                )
                apply_ledger_update = False

            if apply_ledger_update:
                await ledger.send_revoc_reg_entry(
                    rev_list.rev_reg_def_id,
                    "CL_ACCUM",
                    recovery_txn,
                    rev_list.issuer_id,
                    write_ledger=write_ledger,
                    endorser_did=endorser_did,
                )

    # Ledger update not applied, return without applied_txn
    return (rev_reg_delta, recovery_txn, applied_txn)
