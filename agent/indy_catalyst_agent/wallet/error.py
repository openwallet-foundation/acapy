"""
Wallet-related exceptions
"""

from ..error import BaseError

class WalletError(BaseError):
    """
    General wallet exception
    """
    pass

class WalletNotFoundError(WalletError):
    """
    Record not found exception
    """
    pass

class WalletDuplicateError(WalletError):
    """
    Duplicate record exception
    """
    pass
