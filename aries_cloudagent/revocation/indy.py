"""Indy revocation registry management."""

from typing import Sequence

from ..config.injection_context import InjectionContext
from ..ledger.base import BaseLedger

from .error import RevocationNotSupportedError
from .models.issuer_rev_reg_record import IssuerRevRegRecord
from .models.revocation_registry import RevocationRegistry


class IndyRevocation:
    """Class for managing Indy credential revocation."""

    def __init__(self, context: InjectionContext):
        """Initialize the IndyRevocation instance."""
        self._context = context

    async def init_issuer_registry(
        self,
        cred_def_id: str,
        issuer_did: str,
        in_advance: bool = True,
        max_cred_num: int = None,
        revoc_def_type: str = None,
        tag: str = None,
    ) -> "IssuerRevRegRecord":
        """Create a new revocation registry record for a credential definition."""
        ledger: BaseLedger = await self._context.inject(BaseLedger)
        async with ledger:
            cred_def = await ledger.get_credential_definition(cred_def_id)
        if not cred_def:
            raise RevocationNotSupportedError("Credential definition not found")
        if not cred_def["value"].get("revocation"):
            raise RevocationNotSupportedError(
                "Credential definition does not support revocation"
            )
        record = IssuerRevRegRecord(
            cred_def_id=cred_def_id,
            issuer_did=issuer_did,
            issuance_type=(
                IssuerRevRegRecord.ISSUANCE_BY_DEFAULT
                if in_advance
                else IssuerRevRegRecord.ISSUANCE_ON_DEMAND
            ),
            max_cred_num=max_cred_num,
            revoc_def_type=revoc_def_type,
            tag=tag,
        )
        await record.save(self._context, reason="Init revocation registry")
        return record

    async def get_active_issuer_rev_reg_record(
        self,
        cred_def_id: str
    ) -> "IssuerRevRegRecord":
        """Return the current active registry for issuing a given credential definition.

        If no registry exists, then a new one will be created.

        Args:
            cred_def_id: ID of the base credential definition
        """
        current = await IssuerRevRegRecord.query_by_cred_def_id(
            self._context,
            cred_def_id,
            IssuerRevRegRecord.STATE_ACTIVE
        )
        return current[0] if current else None

    async def get_issuer_rev_reg_record(
        self, revoc_reg_id: str
    ) -> "IssuerRevRegRecord":
        """Return a revocation registry record by identifier.

        Args:
            revoc_reg_id: ID of the revocation registry
        """
        return await IssuerRevRegRecord.retrieve_by_revoc_reg_id(
            self._context, revoc_reg_id
        )

    async def list_issuer_registries(self) -> Sequence["IssuerRevRegRecord"]:
        """List the issuer's current revocation registries."""
        return await IssuerRevRegRecord.query(self._context)

    async def get_ledger_registry(self, revoc_reg_id: str) -> "RevocationRegistry":
        """Get a revocation registry from the ledger, fetching as necessary."""
        ledger: BaseLedger = await self._context.inject(BaseLedger)
        async with ledger:
            revoc_reg_def = await ledger.get_revoc_reg_def(revoc_reg_id)
            # TODO apply caching here?
            return RevocationRegistry.from_definition(revoc_reg_def, True)
