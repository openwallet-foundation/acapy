"""Ledger related errors."""

from typing import Any, Generic, Optional, TypeVar
from ..core.error import BaseError


class LedgerError(BaseError):
    """Base class for ledger errors."""


class LedgerConfigError(LedgerError):
    """Base class for ledger configuration errors."""


class BadLedgerRequestError(LedgerError):
    """The current request cannot proceed."""


class ClosedPoolError(LedgerError):
    """Indy pool is closed."""


class LedgerTransactionError(LedgerError):
    """The ledger rejected the transaction."""


T = TypeVar("T")


class LedgerObjectAlreadyExistsError(LedgerError, Generic[T]):
    """Raised when a ledger object already existed."""

    def __init__(self, message: Optional[str] = None, obj: T = None, *args, **kwargs):
        super().__init__(message, obj, *args, **kwargs)
        self.obj = obj

    @property
    def message(self):
        if self.args[0] and self.args[1]:
            return f"{self.args[0]}: {self.args[1]}"
        else:
            return super().message
