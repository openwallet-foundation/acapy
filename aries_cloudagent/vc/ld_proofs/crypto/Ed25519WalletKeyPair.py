from ....wallet.base import BaseWallet
from ....wallet.util import public_key_base58_to_fingerprint
from .KeyPair import KeyPair


class Ed25519WalletKeyPair(KeyPair):
    def __init__(self, wallet: BaseWallet, public_key_base58: str):
        self.wallet = wallet
        self.public_key_base58 = public_key_base58

    def fingerprint(self) -> str:
        return public_key_base58_to_fingerprint(self.public_key_base58)

    async def sign(self, message: bytes) -> bytes:
        return await self.wallet.sign_message(
            message,
            self.public_key_base58,
        )

    async def verify(self, message: bytes, signature: bytes) -> bool:
        return await self.wallet.verify_message(
            message, signature, self.public_key_base58
        )
