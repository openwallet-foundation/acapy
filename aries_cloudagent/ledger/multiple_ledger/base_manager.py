"""Manager for multiple ledger."""

from abc import ABC, abstractmethod
from typing import Optional, Tuple, Mapping, List

from ...core.error import BaseError
from ...core.profile import Profile
from ...ledger.base import BaseLedger
from ...messaging.valid import IndyDID


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
    async def set_profile_write_ledger(self, ledger_id: str, profile: Profile) -> str:
        """Set the write ledger for the profile."""

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
