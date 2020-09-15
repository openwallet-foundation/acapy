"""Classes to manage credential revocation."""

import asyncio
import json
import logging
from typing import Mapping, Sequence, Text, Tuple

from ..config.injection_context import InjectionContext
from ..core.error import BaseError
from ..issuer.base import BaseIssuer
from ..protocols.issue_credential.v1_0.models.credential_exchange import (
    V10CredentialExchange
)
from ..storage.base import BaseStorage
from ..storage.error import StorageNotFoundError

from .indy import IndyRevocation
from .models.revocation_registry import RevocationRegistry
from .models.issuer_rev_reg_record import IssuerRevRegRecord
from .models.issuer_cred_rev_record import IssuerCredRevRecord


class RevocationManagerError(BaseError):
    """Revocation manager error."""


class RevocationManager:
    """Class for managing revocation operations."""

    def __init__(self, context: InjectionContext):
        """
        Initialize a RevocationManager.

        Args:
            context: The context for this revocation manager
        """
        self._context = context
        self._logger = logging.getLogger(__name__)

    @property
    def context(self) -> InjectionContext:
        """
        Accessor for the current request context.

        Returns:
            The request context for this connection

        """
        return self._context

    async def revoke_credential_by_cred_ex_id(
        self, cred_ex_id: str, publish: bool = False
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
            rec = await IssuerCredRevRecord.retrieve_by_cred_ex_id(
                self.context,
                cred_ex_id,
                cred_ex,
            )
        except StorageNotFoundError as err:
            raise RevocationManagerError(
                "No issuer credential revocation record found for "
                f"credential exchange id {cred_ex_id}"
            )
        return await self.revoke_credential(
            rev_reg_id=rec.rev_reg_id,
            cred_rev_id=cred_rev_id,
            publish=publish
        )

    async def revoke_credential(
        self, rev_reg_id: str, cred_rev_id: str, publish: bool = False
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
        issuer: BaseIssuer = await self.context.inject(BaseIssuer)

        revoc = IndyRevocation(self.context)
        registry_record = await revoc.get_issuer_rev_reg_record(rev_reg_id)
        if not registry_record:
            raise RevocationManagerManagerError(
                f"No revocation registry record found for id {rev_reg_id}"
            )

        if publish:
            rev_reg = await revoc.get_ledger_registry(rev_reg_id)
            await rev_reg.get_or_fetch_local_tails_path()

            # pick up pending revocations on input revocation registry
            crids = list(set(registry_record.pending_pub + [cred_rev_id]))
            (delta_json, _) = await issuer.revoke_credentials(
                registry_record.revoc_reg_id, registry_record.tails_local_path, crids
            )
            if delta_json:
                registry_record.revoc_reg_entry = json.loads(delta_json)
                await registry_record.publish_registry_entry(self.context)
                await registry_record.clear_pending(self.context)

        else:
            await registry_record.mark_pending(self.context, cred_rev_id)

    async def publish_pending_revocations(
        self, rrid2crid: Mapping[Text, Sequence[Text]] = None
    ) -> Mapping[Text, Sequence[Text]]:
        """
        Publish pending revocations to the ledger.

        Args:
            rrid2crid: Mapping from revocation registry identifiers to all credential
                revocation identifiers within each to publish. Specify null/empty map
                for all revocation registries. Specify empty sequence per revocation
                registry identifier for all pending within the revocation registry;
                e.g.,

            ::

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
        issuer: BaseIssuer = await self.context.inject(BaseIssuer)

        registry_records = await IssuerRevRegRecord.query_by_pending(self.context)
        for registry_record in registry_records:
            rrid = registry_record.revoc_reg_id
            crids = []
            if not rrid2crid:
                crids = registry_record.pending_pub
            elif rrid in rrid2crid:
                crids = [
                    crid
                    for crid in registry_record.pending_pub
                    if crid in (rrid2crid[rrid] or []) or not rrid2crid[rrid]
                ]
            if crids:
                (delta_json, failed_crids) = await issuer.revoke_credentials(
                    registry_record.revoc_reg_id,
                    registry_record.tails_local_path,
                    crids,
                )
                registry_record.revoc_reg_entry = json.loads(delta_json)
                await registry_record.publish_registry_entry(self.context)
                published = [crid for crid in crids if crid not in failed_crids]
                result[registry_record.revoc_reg_id] = published
                await registry_record.clear_pending(self.context, published)

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

            ::

                {} - clear all pending revocations from all revocation registries
                {
                    "R17v42T4pk...:4:R17v42T4pk...:3:CL:19:tag:CL_ACCUM:0": [],
                    "R17v42T4pk...:4:R17v42T4pk...:3:CL:19:tag:CL_ACCUM:1": ["1", "2"]
                } - clear:
                    - all pending revocations from all revocation registry tagged 0
                    - pending ["1", "2"] from revocation registry tagged 1
                    - no pending revocations from any other revocation registries.

        Returns:
            mapping from revocation registry id to its remaining
            cred rev ids still marked pending, omitting revocation registries
            with no remaining pending publications.

        """
        result = {}
        registry_records = await IssuerRevRegRecord.query_by_pending(self.context)
        for registry_record in registry_records:
            rrid = registry_record.revoc_reg_id
            await registry_record.clear_pending(self.context, (purge or {}).get(rrid))
            if registry_record.pending_pub:
                result[rrid] = registry_record.pending_pub

        return result
