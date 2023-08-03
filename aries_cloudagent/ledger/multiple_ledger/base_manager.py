"""Manager for multiple ledger."""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, Mapping, List

from ...core.error import BaseError
from ...core.profile import Profile
from ...ledger.base import BaseLedger
from ...messaging.valid import IndyDID
from ...multitenant.manager import BaseMultitenantManager


class MultipleLedgerManagerError(BaseError):
    """Generic multiledger error."""


class BaseMultipleLedgerManager(ABC):
    """Base class for handling multiple ledger support."""

    def __init__(self, profile: Profile):
        """Initialize Multiple Ledger Manager."""

    @abstractmethod
    def get_endorser_info_for_ledger(self, ledger_id: str) -> Optional[Tuple[str, str]]:
        """Return endorser alias, did tuple for provided ledger, if available."""

    @abstractmethod
    async def get_write_ledgers(self) -> List[str]:
        """Return write ledger."""

    @abstractmethod
    async def get_ledger_id_by_ledger_pool_name(self, pool_name: str) -> str:
        """Return ledger_id by ledger pool name."""

    @abstractmethod
    async def get_prod_ledgers(self) -> Mapping:
        """Return configured production ledgers."""

    @abstractmethod
    async def get_nonprod_ledgers(self) -> Mapping:
        """Return configured non production ledgers."""

    @abstractmethod
    async def _get_ledger_by_did(
        self, ledger_id: str, did: str
    ) -> Optional[Tuple[str, BaseLedger, bool]]:
        """Build and submit GET_NYM request and process response."""

    @abstractmethod
    async def get_ledger_inst_by_id(self, ledger_id: str) -> Optional[BaseLedger]:
        """Return ledger instance by identifier."""

    @abstractmethod
    async def lookup_did_in_configured_ledgers(
        self, did: str, cache_did: bool
    ) -> Tuple[str, BaseLedger]:
        """Lookup given DID in configured ledgers in parallel."""

    def extract_did_from_identifier(self, identifier: str) -> str:
        """Return did from record identifier (REV_REG_ID, CRED_DEF_ID, SCHEMA_ID)."""
        if bool(IndyDID.PATTERN.match(identifier)):
            return identifier.split(":")[-1]
        else:
            return identifier.split(":")[0]

    async def set_profile_write_ledger(self, ledger_id: str, profile: Profile) -> str:
        """Set the write ledger for the profile."""
        if ledger_id not in self.writable_ledgers:
            raise MultipleLedgerManagerError(
                f"Provided Ledger identifier {ledger_id} is not write configurable."
            )
        extra_settings = {}
        multi_tenant_mgr = self.profile.inject_or(BaseMultitenantManager)
        multi_ledgers = self.production_ledgers | self.non_production_ledgers
        if ledger_id in multi_ledgers:
            profile.context.injector.bind_instance(
                BaseLedger, multi_ledgers.get(ledger_id)
            )
            self._update_settings(profile.context.settings, ledger_id)
            self._update_settings(extra_settings, ledger_id)
            if multi_tenant_mgr:
                await multi_tenant_mgr.update_wallet(
                    profile.context.settings["wallet.id"],
                    extra_settings,
                )
            return ledger_id
        raise MultipleLedgerManagerError(f"No ledger info found for {ledger_id}.")

    def _update_settings(self, settings, ledger_id: str):
        endorser_info = self.get_endorser_info_for_ledger(ledger_id)
        if endorser_info:
            endorser_alias, endorser_did = endorser_info
            settings["endorser.endorser_alias"] = endorser_alias
            settings["endorser.endorser_public_did"] = endorser_did
        settings["ledger.write_ledger"] = ledger_id
