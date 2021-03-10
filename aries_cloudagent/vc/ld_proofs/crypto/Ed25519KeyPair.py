from typing import Optional
from base58 import b58decode, b58encode
from nacl.encoding import Base64Encoder
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey, SigningKey

from .KeyPair import KeyPair
from ....wallet.base import BaseWallet


class Ed25519KeyPair(KeyPair):
    def __init__(self, public_key_base_58: bytes):
        self.public_key = b58decode(public_key_base_58)
        self.verifier = VerifyKey(self.public_key)
        self.signer: Optional[SigningKey] = None

    @classmethod
    def generate(cls, seed: str = None) -> "Ed25519KeyPair":
        if seed:
            signer = SigningKey(seed)
        else:
            signer = SigningKey.generate()

        key_pair = cls(b58encode(signer.verify_key._key))
        key_pair.signer = signer
        key_pair.public_key = key_pair.verifier._key
        key_pair.private_key = signer._signing_key

        return key_pair

    async def sign(self, message: bytes) -> bytes:
        if not self.signer:
            raise Exception("No signer defined")

        return self.signer.sign(message, Base64Encoder).signature

    async def verify(self, message: bytes) -> bool:
        try:
            self.verifier.verify(message)
            return True
        except BadSignatureError:
            return False


class Ed25519WalletKeyPair(KeyPair):
    def __init__(self, verkey: str, wallet: BaseWallet):
        self.verkey = verkey
        self.wallet = wallet

    async def sign(self, message: bytes) -> bytes:
        return await self.wallet.sign_message(
            message,
            self.verkey,
        )

    async def verify(self, message: bytes, signature: bytes) -> bool:
        return await self.wallet.verify_message(message, signature, self.verkey)
