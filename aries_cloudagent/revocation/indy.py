"""Indy revocation registry management."""

from typing import Sequence

from ..config.injection_context import InjectionContext
from ..ledger.base import BaseLedger

from .error import RevocationNotSupportedError
from .models.issuer_revocation_record import IssuerRevocationRecord
from .models.revocation_registry import RevocationRegistry


class IndyRevocation:
    """Class for managing Indy credential revocation."""

    REGISTRY_CACHE = {}

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
    ) -> "IssuerRevocationRecord":
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
        record = IssuerRevocationRecord(
            cred_def_id=cred_def_id,
            issuer_did=issuer_did,
            issuance_type=(
                IssuerRevocationRecord.ISSUANCE_BY_DEFAULT
                if in_advance
                else IssuerRevocationRecord.ISSUANCE_ON_DEMAND
            ),
            max_cred_num=max_cred_num,
            revoc_def_type=revoc_def_type,
            tag=tag,
        )
        await record.save(self._context, reason="Init revocation registry")
        self.REGISTRY_CACHE[cred_def_id] = record.record_id
        return record

    async def get_active_issuer_revocation_record(
        self, cred_def_id: str, await_create: bool = False
    ) -> "IssuerRevocationRecord":
        """Return the current active registry for issuing a given credential definition.

        If no registry exists, then a new one will be created.

        Args:
            cred_def_id: ID of the base credential definition
            await_create: Wait for the registry and tails file to be created, if needed
        """
        # FIXME filter issuing registries by cred def, state (active or full), pick one
        if cred_def_id in self.REGISTRY_CACHE:
            registry = await IssuerRevocationRecord.retrieve_by_id(
                self._context, self.REGISTRY_CACHE[cred_def_id]
            )
            return registry

    async def get_issuer_revocation_record(
        self, revoc_reg_id: str
    ) -> "IssuerRevocationRecord":
        """Return the current active registry for issuing a given credential definition.

        If no registry exists, then a new one will be created.

        Args:
            cred_def_id: ID of the base credential definition
            await_create: Wait for the registry and tails file to be created, if needed
        """
        # FIXME handle exception
        return await IssuerRevocationRecord.retrieve_by_revoc_reg_id(
            self._context, revoc_reg_id
        )

    async def list_issuer_registries(self) -> Sequence["IssuerRevocationRecord"]:
        """List the current revocation registries."""
        # return list of records (need filters)

    async def get_ledger_registry(self, revoc_reg_id: str) -> "RevocationRegistry":
        """Get a revocation registry from the ledger, fetching as necessary."""
        ledger: BaseLedger = await self._context.inject(BaseLedger)
        async with ledger:
            revoc_reg_def = await ledger.get_revoc_reg_def(revoc_reg_id)
            # TODO apply caching here?
            return RevocationRegistry.from_definition(revoc_reg_def, True)
