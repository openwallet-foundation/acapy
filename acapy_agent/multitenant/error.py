"""Multitenant error classes."""

from ..core.error import BaseError


class MultitenantManagerError(BaseError):
    """Generic multitenant error."""


class InvalidTokenError(MultitenantManagerError):
    """Exception raised for invalid tokens."""

    def __init__(self, message: str = "Token not valid"):
        """Initialize an instance of InvalidTokenError."""
        super().__init__(message)


class WalletKeyMissingError(BaseError):
    """Wallet key missing exception."""
