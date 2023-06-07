"""Classes to manage credential revocation."""

import logging
from typing import Mapping, Optional, Sequence, Text, Tuple

from ..anoncreds.default.legacy_indy.registry import LegacyIndyRegistry
from ..anoncreds.revocation import AnonCredsRevocation
from ..core.error import BaseError
from ..core.profile import Profile
from ..protocols.issue_credential.v1_0.models.credential_exchange import (
    V10CredentialExchange,
)
from ..protocols.issue_credential.v2_0.models.cred_ex_record import V20CredExRecord
from ..protocols.revocation_notification.v1_0.models.rev_notification_record import (
    RevNotificationRecord,
)
from ..storage.error import StorageNotFoundError
from .models.issuer_cred_rev_record import IssuerCredRevRecord
from .util import notify_pending_cleared_event, notify_revocation_published_event


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
        revoc = AnonCredsRevocation(self._profile)
        rev_reg_def = await revoc.get_created_revocation_registry_definition(rev_reg_id)
        if not rev_reg_def:
            raise RevocationManagerError(
                f"No revocation registry record found for id: {rev_reg_id}"
            )

        if publish:
            await revoc.get_or_fetch_local_tails_path(rev_reg_def)
            result = await revoc.revoke_pending_credentials(
                rev_reg_id,
                additional_crids=[int(cred_rev_id)],
            )

            if result.curr and result.revoked:
                await self.set_cred_revoked_state(rev_reg_id, result.revoked)
                await revoc.update_revocation_list(
                    rev_reg_id, result.prev, result.curr, result.revoked
                )
            await notify_revocation_published_event(
                self._profile, rev_reg_id, [cred_rev_id]
            )

        else:
            await revoc.mark_pending_revocations(rev_reg_id, int(cred_rev_id))

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

    async def update_rev_reg_revoked_state(
        self,
        rev_reg_def_id: str,
        apply_ledger_update: bool,
        genesis_transactions: str,
    ) -> Tuple[dict, dict, dict]:
        """
        Request handler to fix ledger entry of credentials revoked against registry.

        This is an indy registry specific operation.

        Args:
            rev_reg_id: revocation registry id
            apply_ledger_update: whether to apply an update to the ledger

        Returns:
            Number of credentials posted to ledger

        """
        revoc = AnonCredsRevocation(self._profile)
        rev_list = await revoc.get_created_revocation_list(rev_reg_def_id)
        if not rev_list:
            raise RevocationManagerError(
                f"No revocation list found for revocation registry id {rev_reg_def_id}"
            )

        indy_registry = LegacyIndyRegistry()

        if await indy_registry.supports(rev_reg_def_id):
            return await indy_registry.fix_ledger_entry(
                self._profile,
                rev_list,
                apply_ledger_update,
                genesis_transactions,
            )

        raise RevocationManagerError(
            "Indy registry does not support revocation registry "
            f"identified by {rev_reg_def_id}"
        )

    async def publish_pending_revocations(
        self,
        rrid2crid: Optional[Mapping[Text, Sequence[Text]]] = None,
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
        published_crids = {}
        revoc = AnonCredsRevocation(self._profile)

        rev_reg_def_ids = await revoc.get_revocation_lists_with_pending_revocations()
        for rrid in rev_reg_def_ids:
            if rrid2crid:
                if rrid not in rrid2crid:
                    continue
                limit_crids = [int(crid) for crid in rrid2crid[rrid]]
            else:
                limit_crids = None

            result = await revoc.revoke_pending_credentials(
                rrid, limit_crids=limit_crids
            )
            if result.curr and result.revoked:
                await self.set_cred_revoked_state(rrid, result.revoked)
                await revoc.update_revocation_list(
                    rrid, result.prev, result.curr, result.revoked
                )
                published_crids[rrid] = sorted(result.revoked)
                await notify_revocation_published_event(
                    self._profile, rrid, [str(crid) for crid in result.revoked]
                )

        return published_crids

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

        revoc = AnonCredsRevocation(self._profile)
        rrids = await revoc.get_revocation_lists_with_pending_revocations()
        async with self._profile.transaction() as txn:
            for rrid in rrids:
                await revoc.clear_pending_revocations(
                    txn,
                    rrid,
                    crid_mask=[int(crid) for crid in (purge or {}).get(rrid, ())],
                )
                remaining = await revoc.get_pending_revocations(rrid)
                if remaining:
                    result[rrid] = remaining
                notify.append(rrid)
            await txn.commit()

        for rrid in notify:
            await notify_pending_cleared_event(self._profile, rrid)

        return result

    async def set_cred_revoked_state(
        self, rev_reg_id: str, cred_rev_ids: Sequence[int]
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
                        txn, rev_reg_id, str(cred_rev_id), for_update=True
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
