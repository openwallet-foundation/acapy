from .KeyPair import KeyPair
from base58 import b58decode, b58encode
from nacl.encoding import Base64Encoder
from nacl.signing import VerifyKey, SigningKey


class Ed25519KeyPair(KeyPair):
    def __init__(self, public_key_base_58: bytes):
        self.public_key = b58decode(public_key_base_58)
        self.verifier = VerifyKey(self.public_key)
        self.signer = None

    @classmethod
    def generate(cls, seed: str = None):
        if seed:
            signer = SigningKey(seed)
        else:
            signer = SigningKey.generate()

        key_pair = cls(b58encode(signer.verify_key._key))
        key_pair.signer = signer
        key_pair.public_key = key_pair.verifier._key
        key_pair.private_key = signer._signing_key

        return key_pair

    def sign(self, message):
        if not self.signer:
            raise Exception("No signer defined")

        return self.signer.sign(message, Base64Encoder)

    def verify(self, message):
        return self.verifier.verify(message)
