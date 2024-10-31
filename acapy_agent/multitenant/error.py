"""Multitenant error classes."""

from ..core.error import BaseError


class MultitenantManagerError(BaseError):
    """Generic multitenant error."""


class WalletKeyMissingError(BaseError):
    """Wallet key missing exception."""
