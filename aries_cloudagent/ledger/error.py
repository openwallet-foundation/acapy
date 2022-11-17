"""Ledger related errors."""

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
