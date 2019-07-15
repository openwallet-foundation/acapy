"""Ledger related errors."""

from ..error import BaseError


class LedgerError(BaseError):
    """Base class for ledger errors."""


class BadLedgerRequestError(LedgerError):
    """The current request cannot proceed."""


class ClosedPoolError(LedgerError):
    """Indy pool is closed."""


class LedgerTransactionError(LedgerError):
    """The ledger rejected the transaction."""


class DuplicateSchemaError(LedgerError):
    """The schema already exists on the ledger."""
