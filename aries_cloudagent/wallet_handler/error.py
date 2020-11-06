"""Wallet_handler related exceptions."""

from ..wallet.error import WalletError


class WalletAccessError(WalletError):
    """Wallet access exception."""


class KeyNotFoundError(WalletError):
    """Missing key exception."""


class WalletMissmatchError(WalletError):
    """Wrong wallet exception."""


class WalletNotFoundError(WalletError):
    """No wallet for given information exception."""


class DuplicateMappingError(WalletError):
    """Mapping already exists exception."""


class WalletDuplicateError(WalletError):
    """Duplicate record exception."""
