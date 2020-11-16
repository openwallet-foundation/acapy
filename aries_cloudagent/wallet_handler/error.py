"""Wallet_handler related exceptions."""

from ..wallet.error import WalletError


class WalletAccessError(WalletError):
    """Wallet access exception."""


class KeyNotFoundError(WalletError):
    """Missing key exception."""


class WalletMissmatchError(WalletError):
    """Wrong wallet exception."""


class DuplicateMappingError(WalletError):
    """Mapping already exists exception."""

