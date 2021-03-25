"""Key pair based on base wallet interface"""

from abc import ABCMeta

from ....wallet.base import BaseWallet
from .KeyPair import KeyPair


class WalletKeyPair(KeyPair, metaclass=ABCMeta):
    """Base wallet key pair"""

    def __init__(self, *, wallet: BaseWallet) -> None:
        """Initialize new WalletKeyPair instance."""
        self.wallet = wallet