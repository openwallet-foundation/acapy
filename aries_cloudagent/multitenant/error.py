"""Multitenant error classes."""

from ..core.error import BaseError


class WalletKeyMissingError(BaseError):
    """Wallet key missing exception."""
