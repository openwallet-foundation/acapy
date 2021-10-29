"""Manager for multiple ledger."""

from abc import ABC, abstractmethod
from typing import TypeVar, List, Optional, Tuple

from ...core.error import BaseError
from ...core.profile import Profile

T = TypeVar("T")


class MultipleLedgerManagerError(BaseError):
    """Generic multiledger error."""


class BaseMultipleLedgerManager(ABC):
    """Base class for handling multiple ledger support."""

    def __init__(self, profile: Profile):
        """Initialize Multiple Ledger Manager."""

    @abstractmethod
    async def get_write_ledger(self) -> Tuple[str, T]:
        """Return write ledger."""

    @abstractmethod
    async def set_write_ledger(self, ledger_id: str = None):
        """Set a ledger as write ledger and update BaseLedger."""

    @abstractmethod
    async def update_profile_context(self, ledger: T):
        """Update BaseLedger and Verifier in context."""

    @abstractmethod
    async def reset_write_ledger(self) -> Tuple[str, T]:
        """Reset the assigned write_ledger and return new write ledger."""

    @abstractmethod
    async def update_ledger_config(self, ledger_config_list: List):
        """Update production and non_production ledgers."""

    @abstractmethod
    async def _get_ledger_by_did(
        self, ledger_id: str, did: str
    ) -> Optional[Tuple[str, T, bool]]:
        """Build and submit GET_NYM request and process response."""

    @abstractmethod
    async def lookup_did_in_configured_ledgers(
        self, did: str, cache_did: bool
    ) -> Tuple[str, T]:
        """Lookup given DID in configured ledgers in parallel."""

    def extract_did_from_identifier(self, identifier: str) -> str:
        """Return did from record identifier (REV_REG_ID, CRED_DEF_ID, SCHEMA_ID)."""
        return identifier.split(":")[0]
