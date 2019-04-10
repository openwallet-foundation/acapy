"""Ledger related errors."""

from ..error import BaseError


class ClosedPoolError(BaseError):
    """Indy pool is closed."""


class LedgerTransactionError(BaseError):
    """The ledger rejected the transaction."""
