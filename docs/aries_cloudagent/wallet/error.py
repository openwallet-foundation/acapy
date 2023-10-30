"""Wallet-related exceptions."""

from ..core.error import BaseError


class WalletError(BaseError):
    """General wallet exception."""


class WalletNotFoundError(WalletError):
    """Record not found exception."""


class WalletDuplicateError(WalletError):
    """Duplicate record exception."""


class WalletSettingsError(WalletError):
    """Invalid settings exception."""
