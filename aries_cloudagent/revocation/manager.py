"""Classes to manage credential revocation."""

import json
import logging
from typing import Mapping, Sequence, Text

from ..protocols.revocation_notification.v1_0.models.rev_notification_record import (
    RevNotificationRecord,
)
from ..core.error import BaseError
from ..core.profile import Profile
from ..indy.issuer import IndyIssuer
from ..storage.error import StorageNotFoundError
from .indy import IndyRevocation
from .models.issuer_cred_rev_record import IssuerCredRevRecord
from .models.issuer_rev_reg_record import IssuerRevRegRecord
from .util import notify_pending_cleared_event, notify_revocation_published_event
from ..protocols.issue_credential.v1_0.models.credential_exchange import (
    V10CredentialExchange,
)
from ..protocols.issue_credential.v2_0.models.cred_ex_record import (
    V20CredExRecord,
)


class RevocationManagerError(BaseError):
    """Revocation manager error."""


class RevocationManager:
    """Class for managing revocation operations."""

    def __init__(self, profile: Profile):
        """
        Initialize a RevocationManager.

        Args:
            context: The context for this revocation manager
        """
        self._profile = profile
        self._logger = logging.getLogger(__name__)

    async def revoke_credential_by_cred_ex_id(
        self,
        cred_ex_id: str,
        publish: bool = False,
        notify: bool = False,
        notify_version: str = None,
        thread_id: str = None,
        connection_id: str = None,
        comment: str = None,
    ):
        """
        Revoke a credential by its credential exchange identifier at issue.

        Optionally, publish the corresponding revocation registry delta to the ledger.

        Args:
            cred_ex_id: credential exchange identifier
            publish: whether to publish the resulting revocation registry delta,
                along with any revocations pending against it

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
            comment=comment,
        )

    async def revoke_credential(
        self,
        rev_reg_id: str,
        cred_rev_id: str,
        publish: bool = False,
        notify: bool = False,
        notify_version: str = None,
        thread_id: str = None,
        connection_id: str = None,
        comment: str = None,
    ):
        """
        Revoke a credential.

        Optionally, publish the corresponding revocation registry delta to the ledger.

        Args:
            rev_reg_id: revocation registry id
            cred_rev_id: credential revocation id
            publish: whether to publish the resulting revocation registry delta,
                along with any revocations pending against it

        """
        issuer = self._profile.inject(IndyIssuer)

        revoc = IndyRevocation(self._profile)
        issuer_rr_rec = await revoc.get_issuer_rev_reg_record(rev_reg_id)
        if not issuer_rr_rec:
            raise RevocationManagerError(
                f"No revocation registry record found for id: {rev_reg_id}"
            )

        if notify:
            thread_id = thread_id or f"indy::{rev_reg_id}::{cred_rev_id}"
            rev_notify_rec = RevNotificationRecord(
                rev_reg_id=rev_reg_id,
                cred_rev_id=cred_rev_id,
                thread_id=thread_id,
                connection_id=connection_id,
                comment=comment,
                version=notify_version,
            )
            async with self._profile.session() as session:
                await rev_notify_rec.save(session, reason="New revocation notification")

        if publish:
            rev_reg = await revoc.get_ledger_registry(rev_reg_id)
            await rev_reg.get_or_fetch_local_tails_path()
            # pick up pending revocations on input revocation registry
            crids = (issuer_rr_rec.pending_pub or []) + [cred_rev_id]
            (delta_json, _) = await issuer.revoke_credentials(
                issuer_rr_rec.revoc_reg_id, issuer_rr_rec.tails_local_path, crids
            )
            async with self._profile.transaction() as txn:
                issuer_rr_upd = await IssuerRevRegRecord.retrieve_by_id(
                    txn, issuer_rr_rec.record_id, for_update=True
                )
                if delta_json:
                    issuer_rr_upd.revoc_reg_entry = json.loads(delta_json)
                await issuer_rr_upd.clear_pending(txn, crids)
                await txn.commit()
            await self.set_cred_revoked_state(rev_reg_id, crids)
            if delta_json:
                await issuer_rr_upd.send_entry(self._profile)
            await notify_revocation_published_event(
                self._profile, rev_reg_id, [cred_rev_id]
            )

        else:
            async with self._profile.transaction() as txn:
                await issuer_rr_rec.mark_pending(txn, cred_rev_id)
                await txn.commit()

    async def update_rev_reg_revoked_state(
        self,
        apply_ledger_update: bool,
        rev_reg_record: IssuerRevRegRecord,
        genesis_transactions: dict,
    ) -> (dict, dict, dict):
        """
        Request handler to fix ledger entry of credentials revoked against registry.

        Args:
            rev_reg_id: revocation registry id
            apply_ledger_update: whether to apply an update to the ledger

        Returns:
            Number of credentials posted to ledger

        """
        return await rev_reg_record.fix_ledger_entry(
            self._profile,
            apply_ledger_update,
            genesis_transactions,
        )

    async def publish_pending_revocations(
        self,
        rrid2crid: Mapping[Text, Sequence[Text]] = None,
    ) -> Mapping[Text, Sequence[Text]]:
        """
        Publish pending revocations to the ledger.

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

        Returns: mapping from each revocation registry id to its cred rev ids published.
        """
        result = {}
        issuer = self._profile.inject(IndyIssuer)

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
                (delta_json, failed_crids) = await issuer.revoke_credentials(
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
                    await issuer_rr_upd.send_entry(self._profile)
                published = sorted(crid for crid in crids if crid not in failed_crids)
                result[issuer_rr_rec.revoc_reg_id] = published
                await notify_revocation_published_event(
                    self._profile, issuer_rr_rec.revoc_reg_id, crids
                )

        return result

    async def clear_pending_revocations(
        self, purge: Mapping[Text, Sequence[Text]] = None
    ) -> Mapping[Text, Sequence[Text]]:
        """
        Clear pending revocation publications.

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
                rrid = issuer_rr_rec.revoc_reg_id
                await issuer_rr_rec.clear_pending(txn, (purge or {}).get(rrid))
                if issuer_rr_rec.pending_pub:
                    result[rrid] = issuer_rr_rec.pending_pub
                notify.append(rrid)
            await txn.commit()

        for rrid in notify:
            await notify_pending_cleared_event(self._profile, rrid)

        return result

    async def set_cred_revoked_state(
        self, rev_reg_id: str, cred_rev_ids: Sequence[str]
    ) -> None:
        """
        Update credentials state to credential_revoked.

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
