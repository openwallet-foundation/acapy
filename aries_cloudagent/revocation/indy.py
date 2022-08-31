"""Indy revocation registry management."""

from typing import Optional, Sequence, Tuple
from uuid import uuid4

from ..core.profile import Profile
from ..ledger.base import BaseLedger
from ..ledger.multiple_ledger.ledger_requests_executor import (
    GET_CRED_DEF,
    GET_REVOC_REG_DEF,
    IndyLedgerRequestsExecutor,
)
from ..multitenant.base import BaseMultitenantManager
from ..protocols.endorse_transaction.v1_0.util import (
    get_endorser_connection_id,
    is_author_role,
)
from ..storage.base import StorageNotFoundError

from .error import (
    RevocationError,
    RevocationNotSupportedError,
    RevocationRegistryBadSizeError,
)
from .models.issuer_rev_reg_record import IssuerRevRegRecord
from .models.revocation_registry import RevocationRegistry
from .util import notify_revocation_reg_init_event


class IndyRevocation:
    """Class for managing Indy credential revocation."""

    REV_REG_CACHE = {}

    def __init__(self, profile: Profile):
        """Initialize the IndyRevocation instance."""
        self._profile = profile

    async def init_issuer_registry(
        self,
        cred_def_id: str,
        max_cred_num: int = None,
        revoc_def_type: str = None,
        tag: str = None,
        create_pending_rev_reg: bool = False,
        endorser_connection_id: str = None,
        notify: bool = True,
    ) -> IssuerRevRegRecord:
        """Create a new revocation registry record for a credential definition."""
        multitenant_mgr = self._profile.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(self._profile)
        else:
            ledger_exec_inst = self._profile.inject(IndyLedgerRequestsExecutor)
        ledger = (
            await ledger_exec_inst.get_ledger_for_identifier(
                cred_def_id,
                txn_record_type=GET_CRED_DEF,
            )
        )[1]
        async with ledger:
            cred_def = await ledger.get_credential_definition(cred_def_id)
        if not cred_def:
            raise RevocationNotSupportedError("Credential definition not found")
        if not cred_def["value"].get("revocation"):
            raise RevocationNotSupportedError(
                "Credential definition does not support revocation"
            )
        if max_cred_num and not (
            RevocationRegistry.MIN_SIZE <= max_cred_num <= RevocationRegistry.MAX_SIZE
        ):
            raise RevocationRegistryBadSizeError(
                f"Bad revocation registry size: {max_cred_num}"
            )

        record_id = str(uuid4())
        issuer_did = cred_def_id.split(":")[0]
        record = IssuerRevRegRecord(
            new_with_id=True,
            record_id=record_id,
            cred_def_id=cred_def_id,
            issuer_did=issuer_did,
            max_cred_num=max_cred_num,
            revoc_def_type=revoc_def_type,
            tag=tag,
        )
        revoc_def_type = record.revoc_def_type
        rtag = record.tag or record_id
        record.revoc_reg_id = f"{issuer_did}:4:{cred_def_id}:{revoc_def_type}:{rtag}"
        async with self._profile.session() as session:
            await record.save(session, reason="Init revocation registry")

        if endorser_connection_id is None and is_author_role(self._profile):
            endorser_connection_id = await get_endorser_connection_id(self._profile)
            if not endorser_connection_id:
                raise RevocationError(reason="Endorser connection not found")

        if notify:
            await notify_revocation_reg_init_event(
                self._profile,
                record.record_id,
                create_pending_rev_reg=create_pending_rev_reg,
                endorser_connection_id=endorser_connection_id,
            )

        return record

    async def handle_full_registry(self, revoc_reg_id: str):
        """Update the registry status and start the next registry generation."""
        async with self._profile.transaction() as txn:
            registry = await IssuerRevRegRecord.retrieve_by_revoc_reg_id(
                txn, revoc_reg_id, for_update=True
            )
            if registry.state == IssuerRevRegRecord.STATE_FULL:
                return
            await registry.set_state(
                txn,
                IssuerRevRegRecord.STATE_FULL,
            )
            await txn.commit()

        await self.init_issuer_registry(
            registry.cred_def_id,
            registry.max_cred_num,
            registry.revoc_def_type,
        )

    async def get_active_issuer_rev_reg_record(
        self, cred_def_id: str
    ) -> IssuerRevRegRecord:
        """Return current active registry for issuing a given credential definition.

        Args:
            cred_def_id: ID of the base credential definition
        """
        async with self._profile.session() as session:
            current = sorted(
                await IssuerRevRegRecord.query_by_cred_def_id(
                    session, cred_def_id, IssuerRevRegRecord.STATE_ACTIVE
                )
            )
        if current:
            return current[0]  # active record is oldest published but not full
        raise StorageNotFoundError(
            f"No active issuer revocation record found for cred def id {cred_def_id}"
        )

    async def get_issuer_rev_reg_record(self, revoc_reg_id: str) -> IssuerRevRegRecord:
        """Return a revocation registry record by identifier.

        Args:
            revoc_reg_id: ID of the revocation registry
        """
        async with self._profile.session() as session:
            return await IssuerRevRegRecord.retrieve_by_revoc_reg_id(
                session, revoc_reg_id
            )

    async def list_issuer_registries(self) -> Sequence[IssuerRevRegRecord]:
        """List the issuer's current revocation registries."""
        async with self._profile.session() as session:
            return await IssuerRevRegRecord.query(session)

    async def get_issuer_rev_reg_delta(
        self, rev_reg_id: str, fro: int = None, to: int = None
    ) -> dict:
        """
        Check ledger for revocation status for a given revocation registry.

        Args:
            rev_reg_id: ID of the revocation registry

        """
        ledger = await self.get_ledger_for_registry(rev_reg_id)
        async with ledger:
            (rev_reg_delta, _) = await ledger.get_revoc_reg_delta(
                rev_reg_id,
                fro,
                to,
            )

        return rev_reg_delta

    async def get_or_create_active_registry(
        self, cred_def_id: str, max_cred_num: int = None
    ) -> Optional[Tuple[IssuerRevRegRecord, RevocationRegistry]]:
        """Fetch the active revocation registry.

        If there is no active registry then creation of a new registry will be
        triggered and the caller should retry after a delay.
        """
        try:
            active_rev_reg_rec = await self.get_active_issuer_rev_reg_record(
                cred_def_id
            )
            rev_reg = active_rev_reg_rec.get_registry()
            await rev_reg.get_or_fetch_local_tails_path()
            return active_rev_reg_rec, rev_reg
        except StorageNotFoundError:
            pass

        async with self._profile.session() as session:
            rev_reg_recs = await IssuerRevRegRecord.query_by_cred_def_id(
                session, cred_def_id, {"$neq": IssuerRevRegRecord.STATE_FULL}
            )
            if not rev_reg_recs:
                await self.init_issuer_registry(
                    cred_def_id,
                    max_cred_num=max_cred_num,
                )
        return None

    async def get_ledger_registry(self, revoc_reg_id: str) -> RevocationRegistry:
        """Get a revocation registry from the ledger, fetching as necessary."""
        if revoc_reg_id in IndyRevocation.REV_REG_CACHE:
            return IndyRevocation.REV_REG_CACHE[revoc_reg_id]

        ledger = await self.get_ledger_for_registry(revoc_reg_id)

        async with ledger:
            rev_reg = RevocationRegistry.from_definition(
                await ledger.get_revoc_reg_def(revoc_reg_id), True
            )
            IndyRevocation.REV_REG_CACHE[revoc_reg_id] = rev_reg
            return rev_reg

    async def get_ledger_for_registry(self, revoc_reg_id: str) -> BaseLedger:
        """Get the ledger for the given registry."""
        multitenant_mgr = self._profile.inject_or(BaseMultitenantManager)
        if multitenant_mgr:
            ledger_exec_inst = IndyLedgerRequestsExecutor(self._profile)
        else:
            ledger_exec_inst = self._profile.inject(IndyLedgerRequestsExecutor)
        ledger = (
            await ledger_exec_inst.get_ledger_for_identifier(
                revoc_reg_id,
                txn_record_type=GET_REVOC_REG_DEF,
            )
        )[1]
        return ledger
