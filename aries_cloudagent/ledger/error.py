"""Ledger related errors."""

from typing import Generic, TypeVar
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

    def __init__(
        self,
        message: str,
        obj_id: str,
        obj: T = None,
        *args,
        **kwargs,
    ):
        """Initialize an instance.

        Args:
            message: Human readable message text
            obj_id: ledger object id
            obj: ledger object

        """
        super().__init__(message, obj_id, obj, *args, **kwargs)
        self._message = message
        self.obj_id = obj_id
        self.obj = obj

    @property
    def message(self):
        """Error message."""
        return f"{self._message}: {self.obj_id}, {self.obj}"
