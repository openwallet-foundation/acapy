"""Wallet-related exceptions."""

from ..error import BaseError


class WalletError(BaseError):
    """General wallet exception."""


class WalletNotFoundError(WalletError):
    """Record not found exception."""


class WalletDuplicateError(WalletError):
    """Duplicate record exception."""
