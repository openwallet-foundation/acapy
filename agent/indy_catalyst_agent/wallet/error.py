"""
Wallet-related exceptions
"""

class WalletException(Exception):
    """
    General wallet exception
    """
    pass

class WalletNotFoundException(WalletException):
    """
    Record not found exception
    """
    pass
