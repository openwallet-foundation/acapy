from ....wallet.base import BaseWallet
from ....did.did_key import DIDKey
from ....wallet.crypto import KeyType
from .KeyPair import KeyPair


class Ed25519WalletKeyPair(KeyPair):
    def __init__(self, wallet: BaseWallet, public_key_base58: str):
        self.wallet = wallet
        self.public_key_base58 = public_key_base58

    def fingerprint(self) -> str:
        return DIDKey.from_public_key_b58(
            self.public_key_base58, KeyType.ED25519
        ).fingerprint

    async def sign(self, message: bytes) -> bytes:
        return await self.wallet.sign_message(
            message,
            self.public_key_base58,
        )

    async def verify(self, message: bytes, signature: bytes) -> bool:
        return await self.wallet.verify_message(
            message, signature, self.public_key_base58
        )
