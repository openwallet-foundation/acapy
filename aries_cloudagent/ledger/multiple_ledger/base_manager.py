from abc import ABC, abstractmethod
from typing import TypeVar, List, Optional, Tuple

from ...core.error import BaseError
from ...core.profile import Profile

T = TypeVar("T")


class MultipleLedgerManagerError(BaseError):
    """Generic multitenant error."""


class BaseMultipleLedgerManager(ABC):
    """Base class for handling multiple ledger support."""

    def __init__(self, profile: Profile):
        """Initialize Multiple Ledger Manager."""
        super().__init__()
        self._profile = profile

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
    async def get_ledger_instance_by_did(self, did: str) -> Optional[T]:
        """Return ledger_instance with DID, if present."""

    def extract_did_from_identifier(self, identifier: str) -> str:
        """Return did from record identifier (REV_REG_ID, CRED_DEF_ID, SCHEMA_ID)."""
        return identifier.split(":")[0]
