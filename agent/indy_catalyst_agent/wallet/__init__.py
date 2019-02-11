"""
Abstract and Indy wallet handling
"""

from .base import BaseWallet, DIDInfo, PairwiseInfo
from .error import WalletError, WalletDuplicateError, WalletNotFoundError
