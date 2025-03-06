"""Classes to manage credential revocation."""

import asyncio
import json
import logging
from typing import Mapping, NamedTuple, Optional, Sequence, Text, Tuple

from ..cache.base import BaseCache
from ..connections.models.conn_record import ConnRecord
from ..core.error import BaseError
from ..core.profile import Profile, ProfileSession
from ..indy.credx.issuer import CATEGORY_REV_REG
from ..indy.issuer import IndyIssuer
from ..ledger.base import BaseLedger
from ..messaging.responder import BaseResponder
from ..protocols.endorse_transaction.v1_0.manager import (
    TransactionManager,
    TransactionManagerError,
)
from ..protocols.endorse_transaction.v1_0.util import (
    get_endorser_connection_id,
)
from ..protocols.issue_credential.v1_0.models.credential_exchange import (
    V10CredentialExchange,
)
from ..protocols.issue_credential.v2_0.models.cred_ex_record import V20CredExRecord
from ..protocols.revocation_notification.v1_0.models.rev_notification_record import (
    RevNotificationRecord,
)
from ..storage.error import StorageError, StorageNotFoundError
from .indy import IndyRevocation
from .models.issuer_cred_rev_record import IssuerCredRevRecord
from .models.issuer_rev_reg_record import IssuerRevRegRecord
from .util import notify_pending_cleared_event, notify_revocation_published_event

LOGGER = logging.getLogger(__name__)


class RevocationManagerError(BaseError):
    """Revocation manager error."""


class RevocationNotificationInfo(NamedTuple):
    """Revocation notification information."""

    rev_reg_id: str
    cred_rev_id: str
    thread_id: Optional[str]
    connection_id: Optional[str]
    comment: Optional[str]
    notify_version: Optional[str]


class RevocationManager:
    """Class for managing revocation operations."""

    def __init__(self, profile: Profile):
        """Initialize a RevocationManager.

        Args:
            profile: The profile instance for this revocation manager
        """
        self._profile = profile
        self._logger = logging.getLogger(__name__)

    async def revoke_credential_by_cred_ex_id(
        self,
        cred_ex_id: str,
        publish: bool = False,
        notify: bool = False,
        notify_version: Optional[str] = None,
        thread_id: Optional[str] = None,
        connection_id: Optional[str] = None,
        endorser_conn_id: Optional[str] = None,
        comment: Optional[str] = None,
        write_ledger: bool = True,
    ):
        """Revoke a credential by its credential exchange identifier at issue.

        Optionally, publish the corresponding revocation registry delta to the ledger.

        Args:
            cred_ex_id (str): The credential exchange identifier.
            publish (bool, optional): Whether to publish the resulting revocation
                registry delta, along with any revocations pending against it.
                Defaults to False.
            notify (bool, optional): Whether to notify the affected parties about the
                revocation. Defaults to False.
            notify_version (str, optional): The version of the notification to use.
                Defaults to None.
            thread_id (str, optional): The thread identifier for the revocation process.
                Defaults to None.
            connection_id (str, optional): The connection identifier for the revocation
                process. Defaults to None.
            endorser_conn_id (str, optional): The endorser connection identifier for the
                revocation process. Defaults to None.
            comment (str, optional): Additional comment or reason for the revocation.
                Defaults to None.
            write_ledger (bool, optional): Whether to write the revocation to the ledger.
                Defaults to True.

        Raises:
            RevocationManagerError: If no issuer credential revocation record is found
                for the given credential exchange identifier.

        Returns:
            The result of the `revoke_credential` method.

        """
        try:
            async with self._profile.session() as session:
                rec = await IssuerCredRevRecord.retrieve_by_cred_ex_id(
                    session,
                    cred_ex_id,
                )
        except StorageNotFoundError as err:
            raise RevocationManagerError(
                "No issuer credential revocation record found for "
                f"credential exchange id {cred_ex_id}"
            ) from err

        return await self.revoke_credential(
            rev_reg_id=rec.rev_reg_id,
            cred_rev_id=rec.cred_rev_id,
            publish=publish,
            notify=notify,
            notify_version=notify_version,
            thread_id=thread_id,
            connection_id=connection_id,
            endorser_conn_id=endorser_conn_id,
            comment=comment,
            write_ledger=write_ledger,
        )

    async def _prepare_revocation_notification(
        self,
        revoc_notif_info: RevocationNotificationInfo,
    ):
        """Saves the revocation notification record, and thread_id if not provided."""
        thread_id = (
            revoc_notif_info.thread_id
            or f"indy::{revoc_notif_info.rev_reg_id}::{revoc_notif_info.cred_rev_id}"
        )
        rev_notify_rec = RevNotificationRecord(
            rev_reg_id=revoc_notif_info.rev_reg_id,
            cred_rev_id=revoc_notif_info.cred_rev_id,
            thread_id=thread_id,
            connection_id=revoc_notif_info.connection_id,
            comment=revoc_notif_info.comment,
            version=revoc_notif_info.notify_version,
        )
        async with self._profile.session() as session:
            await rev_notify_rec.save(session, reason="New revocation notification")

    async def _get_endorsement_txn_for_revocation(
        self, endorser_conn_id: str, issuer_rr_upd: IssuerRevRegRecord
    ):
        async with self._profile.session() as session:
            try:
                connection_record = await ConnRecord.retrieve_by_id(
                    session, endorser_conn_id
                )
            except StorageNotFoundError:
                raise RevocationManagerError(
                    f"No endorser connection record found for id: {endorser_conn_id}"
                )
            endorser_info = await connection_record.metadata_get(session, "endorser_info")
        endorser_did = endorser_info["endorser_did"]
        return await issuer_rr_upd.send_entry(
            self._profile,
            write_ledger=False,
            endorser_did=endorser_did,
        )

    async def revoke_credential(
        self,
        rev_reg_id: str,
        cred_rev_id: str,
        publish: bool = False,
        notify: bool = False,
        notify_version: Optional[str] = None,
        thread_id: Optional[str] = None,
        connection_id: Optional[str] = None,
        endorser_conn_id: Optional[str] = None,
        comment: Optional[str] = None,
        write_ledger: bool = True,
    ) -> Optional[dict]:
        """Revoke a credential.

        Optionally, publish the corresponding revocation registry delta to the ledger.

        Args:
            rev_reg_id (str): The revocation registry id.
            cred_rev_id (str): The credential revocation id.
            publish (bool, optional): Whether to publish the resulting revocation
                registry delta, along with any revocations pending against it.
                Defaults to False.
            notify (bool, optional): Whether to send a revocation notification.
                Defaults to False.
            notify_version (str, optional): The version of the revocation notification.
                Defaults to None.
            thread_id (str, optional): The thread id for the revocation notification.
                Defaults to None.
            connection_id (str, optional): The connection id for the revocation
                notification. Defaults to None.
            endorser_conn_id (str, optional): The endorser connection id.
                Defaults to None.
            comment (str, optional): Additional comment for the revocation notification.
                Defaults to None.
            write_ledger (bool, optional): Whether to write the revocation entry to the
                ledger. Defaults to True.

        Returns:
            Optional[dict]: The revocation entry response if publish is True and
                write_ledger is True, otherwise None.
        """
        issuer = self._profile.inject(IndyIssuer)
        revoc = IndyRevocation(self._profile)

        issuer_rr_rec = await revoc.get_issuer_rev_reg_record(rev_reg_id)
        if not issuer_rr_rec:
            raise RevocationManagerError(
                f"No revocation registry record found for id: {rev_reg_id}"
            )

        if notify:
            await self._prepare_revocation_notification(
                RevocationNotificationInfo(
                    rev_reg_id=rev_reg_id,
                    cred_rev_id=cred_rev_id,
                    thread_id=thread_id,
                    connection_id=connection_id,
                    comment=comment,
                    notify_version=notify_version,
                ),
            )

        if not publish:
            # If not publishing, just mark the revocation as pending.
            async with self._profile.transaction() as txn:
                await issuer_rr_rec.mark_pending(txn, cred_rev_id)
                await txn.commit()
            return None

        rev_reg = await revoc.get_ledger_registry(rev_reg_id)
        await rev_reg.get_or_fetch_local_tails_path()
        # pick up pending revocations on input revocation registry
        crids = (issuer_rr_rec.pending_pub or []) + [cred_rev_id]
        (delta_json, _) = await issuer.revoke_credentials(
            issuer_rr_rec.cred_def_id,
            issuer_rr_rec.revoc_reg_id,
            issuer_rr_rec.tails_local_path,
            crids,
        )

        # Update the revocation registry record with the new delta
        # and clear pending revocations
        async with self._profile.transaction() as txn:
            issuer_rr_upd = await IssuerRevRegRecord.retrieve_by_id(
                txn, issuer_rr_rec.record_id, for_update=True
            )
            if delta_json:
                issuer_rr_upd.revoc_reg_entry = json.loads(delta_json)
            await issuer_rr_upd.clear_pending(txn, crids)
            await txn.commit()

        await self.set_cred_revoked_state(rev_reg_id, crids)

        # Revocation list needs to be updated on ledger
        if delta_json:
            # Can write to ledger directly
            if write_ledger:
                rev_entry_resp = await issuer_rr_upd.send_entry(self._profile)
                await notify_revocation_published_event(
                    self._profile, rev_reg_id, [cred_rev_id]
                )
                return rev_entry_resp
            # Author --> Need endorsed transaction for revocation
            else:
                return await self._get_endorsement_txn_for_revocation(
                    endorser_conn_id, issuer_rr_upd
                )

    async def update_rev_reg_revoked_state(
        self,
        apply_ledger_update: bool,
        rev_reg_record: IssuerRevRegRecord,
        genesis_transactions: dict,
    ) -> Tuple[dict, dict, dict]:
        """Request handler to fix ledger entry of credentials revoked against registry.

        Args:
            apply_ledger_update (bool): Whether to apply an update to the ledger.
            rev_reg_record (IssuerRevRegRecord): The revocation registry record.
            genesis_transactions (dict): The genesis transactions.

        Returns:
            Tuple[dict, dict, dict]: A tuple containing the number of credentials posted
                to the ledger.

        """
        return await rev_reg_record.fix_ledger_entry(
            self._profile,
            apply_ledger_update,
            genesis_transactions,
        )

    async def publish_pending_revocations(
        self,
        rrid2crid: Mapping[Text, Sequence[Text]] = None,
        write_ledger: bool = True,
        connection_id: Optional[str] = None,
    ) -> Tuple[Optional[dict], Mapping[Text, Sequence[Text]]]:
        """Publish pending revocations to the ledger.

        Args:
            rrid2crid: Mapping from revocation registry identifiers to all credential
                revocation identifiers within each to publish. Specify null/empty map
                for all revocation registries. Specify empty sequence per revocation
                registry identifier for all pending within the revocation registry;
                e.g.,

                {} - publish all pending revocations from all revocation registries

                {
                    "R17v42T4pk...:4:R17v42T4pk...:3:CL:19:tag:CL_ACCUM:0": [],
                    "R17v42T4pk...:4:R17v42T4pk...:3:CL:19:tag:CL_ACCUM:1": ["1", "2"]

                } - publish:
                    - all pending revocations from all revocation registry tagged 0
                    - pending ["1", "2"] from revocation registry tagged 1
                    - no pending revocations from any other revocation registries.
            write_ledger: whether to write the revocation registry entry to the ledger
            connection_id: connection identifier for endorser connection to use

        Returns: mapping from each revocation registry id to its cred rev ids published.
        """
        result = {}
        issuer = self._profile.inject(IndyIssuer)
        rev_entry_responses = []
        async with self._profile.session() as session:
            issuer_rr_recs = await IssuerRevRegRecord.query_by_pending(session)

        for issuer_rr_rec in issuer_rr_recs:
            rrid = issuer_rr_rec.revoc_reg_id
            if rrid2crid:
                if rrid not in rrid2crid:
                    continue
                limit_crids = rrid2crid[rrid]
            else:
                limit_crids = ()
            crids = set(issuer_rr_rec.pending_pub or ())
            if limit_crids:
                crids = crids.intersection(limit_crids)
            if crids:
                crids = list(crids)
                (delta_json, failed_crids) = await issuer.revoke_credentials(
                    issuer_rr_rec.cred_def_id,
                    issuer_rr_rec.revoc_reg_id,
                    issuer_rr_rec.tails_local_path,
                    crids,
                )
                async with self._profile.transaction() as txn:
                    issuer_rr_upd = await IssuerRevRegRecord.retrieve_by_id(
                        txn, issuer_rr_rec.record_id, for_update=True
                    )
                    if delta_json:
                        issuer_rr_upd.revoc_reg_entry = json.loads(delta_json)
                    await issuer_rr_upd.clear_pending(txn, crids)
                    await txn.commit()
                await self.set_cred_revoked_state(issuer_rr_rec.revoc_reg_id, crids)
                if delta_json:
                    if connection_id:
                        async with self._profile.session() as session:
                            try:
                                connection_record = await ConnRecord.retrieve_by_id(
                                    session, connection_id
                                )
                            except StorageNotFoundError:
                                raise RevocationManagerError(
                                    "No endorser connection record found "
                                    f"for id: {connection_id}"
                                )
                            endorser_info = await connection_record.metadata_get(
                                session, "endorser_info"
                            )
                        endorser_did = endorser_info["endorser_did"]
                        rev_entry_responses.append(
                            await issuer_rr_upd.send_entry(
                                self._profile,
                                write_ledger=write_ledger,
                                endorser_did=endorser_did,
                            )
                        )
                    else:
                        rev_entry_responses.append(
                            await issuer_rr_upd.send_entry(self._profile)
                        )
                        await notify_revocation_published_event(
                            self._profile, issuer_rr_rec.revoc_reg_id, crids
                        )
                published = sorted(crid for crid in crids if crid not in failed_crids)
                result[issuer_rr_rec.revoc_reg_id] = published

        return rev_entry_responses, result

    async def clear_pending_revocations(
        self, purge: Mapping[Text, Sequence[Text]] = None
    ) -> Mapping[Text, Sequence[Text]]:
        """Clear pending revocation publications.

        Args:
            purge: Mapping from revocation registry identifiers to all credential
                revocation identifiers within each to clear. Specify null/empty map
                for all revocation registries. Specify empty sequence per revocation
                registry identifier for all pending within the revocation registry;
                e.g.,

                {} - clear all pending revocations from all revocation registries

                {
                    "R17v42T4pk...:4:R17v42T4pk...:3:CL:19:tag:CL_ACCUM:0": [],
                    "R17v42T4pk...:4:R17v42T4pk...:3:CL:19:tag:CL_ACCUM:1": ["1", "2"]

                } - clear
                    - all pending revocations from all revocation registry tagged 0
                    - pending ["1", "2"] from revocation registry tagged 1
                    - no pending revocations from any other revocation registries.

        Returns:
            mapping from revocation registry id to its remaining
            cred rev ids still marked pending, omitting revocation registries
            with no remaining pending publications.

        """
        result = {}
        notify = []

        async with self._profile.transaction() as txn:
            issuer_rr_recs = await IssuerRevRegRecord.query_by_pending(txn)
            for issuer_rr_rec in issuer_rr_recs:
                if purge and issuer_rr_rec.revoc_reg_id not in purge:
                    continue
                rrid = issuer_rr_rec.revoc_reg_id
                await issuer_rr_rec.clear_pending(txn, (purge or {}).get(rrid))
                result[rrid] = issuer_rr_rec.pending_pub
                notify.append(rrid)
            await txn.commit()

        for rrid in notify:
            await notify_pending_cleared_event(self._profile, rrid)

        return result

    async def set_cred_revoked_state(
        self, rev_reg_id: str, cred_rev_ids: Sequence[str]
    ) -> None:
        """Update credentials state to credential_revoked.

        Args:
            rev_reg_id: revocation registry ID
            cred_rev_ids: list of credential revocation IDs

        Returns:
            None

        """
        for cred_rev_id in cred_rev_ids:
            cred_ex_id = None

            try:
                async with self._profile.transaction() as txn:
                    rev_rec = await IssuerCredRevRecord.retrieve_by_ids(
                        txn, rev_reg_id, cred_rev_id, for_update=True
                    )
                    cred_ex_id = rev_rec.cred_ex_id
                    cred_ex_version = rev_rec.cred_ex_version
                    rev_rec.state = IssuerCredRevRecord.STATE_REVOKED
                    await rev_rec.save(txn, reason="revoke credential")
                    await txn.commit()
            except StorageNotFoundError:
                continue

            async with self._profile.transaction() as txn:
                if (
                    not cred_ex_version
                    or cred_ex_version == IssuerCredRevRecord.VERSION_1
                ):
                    try:
                        cred_ex_record = await V10CredentialExchange.retrieve_by_id(
                            txn, cred_ex_id, for_update=True
                        )
                        cred_ex_record.state = (
                            V10CredentialExchange.STATE_CREDENTIAL_REVOKED
                        )
                        await cred_ex_record.save(txn, reason="revoke credential")
                        await txn.commit()
                        continue  # skip 2.0 record check
                    except StorageNotFoundError:
                        pass

                if (
                    not cred_ex_version
                    or cred_ex_version == IssuerCredRevRecord.VERSION_2
                ):
                    try:
                        cred_ex_record = await V20CredExRecord.retrieve_by_id(
                            txn, cred_ex_id, for_update=True
                        )
                        cred_ex_record.state = V20CredExRecord.STATE_CREDENTIAL_REVOKED
                        await cred_ex_record.save(txn, reason="revoke credential")
                        await txn.commit()
                    except StorageNotFoundError:
                        pass

    async def _get_endorser_info(self) -> Tuple[Optional[str], Optional[ConnRecord]]:
        connection_id = await get_endorser_connection_id(self._profile)

        endorser_did = None
        async with self._profile.session() as session:
            connection_record = await ConnRecord.retrieve_by_id(session, connection_id)
            endorser_info = await connection_record.metadata_get(session, "endorser_info")
        endorser_did = endorser_info.get("endorser_did")

        return endorser_did, connection_record

    async def fix_and_publish_from_invalid_accum_err(self, err_msg: str):
        """Fix and publish revocation registry entries from invalid accumulator error."""
        cache = self._profile.inject_or(BaseCache)

        async def check_retry(accum):
            """Used to manage retries for fixing revocation registry entries."""
            retry_value = await cache.get(accum)
            if not retry_value:
                await cache.set(accum, 5)
            else:
                if retry_value > 0:
                    await cache.set(accum, retry_value - 1)
                else:
                    LOGGER.error(
                        f"Revocation registry entry transaction failed for {accum}"
                    )

        def get_genesis_transactions():
            """Get the genesis transactions needed for fixing broken accum."""
            genesis_transactions = self._profile.context.settings.get(
                "ledger.genesis_transactions"
            )
            if not genesis_transactions:
                write_ledger = self._profile.context.injector.inject(BaseLedger)
                pool = write_ledger.pool
                genesis_transactions = pool.genesis_txns
            return genesis_transactions

        async def sync_accumulator(session: ProfileSession):
            """Sync the local accumulator with the ledger and create recovery txn."""
            rev_reg_record = await IssuerRevRegRecord.retrieve_by_id(
                session, rev_reg_entry.name
            )

            # Fix and get the recovery transaction
            (
                rev_reg_delta,
                recovery_txn,
                applied_txn,
            ) = await rev_reg_record.fix_ledger_entry(
                self._profile, False, genesis_transactions
            )

            # Update locally assuming ledger write will succeed
            rev_reg = await session.handle.fetch(
                CATEGORY_REV_REG,
                rev_reg_entry.value_json["revoc_reg_id"],
                for_update=True,
            )
            new_value_json = rev_reg.value_json
            new_value_json["value"]["accum"] = recovery_txn["value"]["accum"]
            await session.handle.replace(
                CATEGORY_REV_REG,
                rev_reg.name,
                json.dumps(new_value_json),
                rev_reg.tags,
            )

            return rev_reg_record, recovery_txn

        async def create_and_send_endorser_txn():
            """Create and send the endorser transaction again."""
            async with ledger:
                # Create the revocation registry entry
                rev_entry_res = await ledger.send_revoc_reg_entry(
                    rev_reg_entry.value_json["revoc_reg_id"],
                    "CL_ACCUM",
                    recovery_txn,
                    rev_reg_record.issuer_did,
                    write_ledger=False,
                    endorser_did=endorser_did,
                )

            # Send the transaction to the endorser again with recovery txn
            transaction_manager = TransactionManager(self._profile)
            try:
                revo_transaction = await transaction_manager.create_record(
                    messages_attach=rev_entry_res["result"],
                    connection_id=connection.connection_id,
                )
                (
                    revo_transaction,
                    revo_transaction_request,
                ) = await transaction_manager.create_request(transaction=revo_transaction)
            except (StorageError, TransactionManagerError) as err:
                raise RevocationManagerError(err.roll_up) from err

            responder = self._profile.inject_or(BaseResponder)
            if not responder:
                raise RevocationManagerError(
                    "No responder found. Unable to send transaction request"
                )
            await responder.send(
                revo_transaction_request,
                connection_id=connection.connection_id,
            )

        async with self._profile.session() as session:
            rev_reg_records = await session.handle.fetch_all(
                IssuerRevRegRecord.RECORD_TYPE
            )
            # Cycle through all rev_rev_def records to find the offending accumulator
            for rev_reg_entry in rev_reg_records:
                ledger = session.inject_or(BaseLedger)
                # Get the value from the ledger
                async with ledger:
                    (accum_response, _) = await ledger.get_revoc_reg_delta(
                        rev_reg_entry.value_json["revoc_reg_id"]
                    )
                    accum = accum_response.get("value", {}).get("accum")

                # If the accum from the ledger matches the error message, fix it
                if accum and accum in err_msg:
                    await check_retry(accum)

                    # Get the genesis transactions needed for fix
                    genesis_transactions = get_genesis_transactions()

                    # We know this needs endorsement
                    endorser_did, connection = await self._get_endorser_info()
                    rev_reg_record, recovery_txn = await sync_accumulator(session=session)
                    await create_and_send_endorser_txn()

                    # Some time in between re-tries
                    await asyncio.sleep(1)
