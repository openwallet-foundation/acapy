from ..crypto import Ed25519KeyPair
from .JwsLinkedDataSignature import JwsLinkedDataSignature


class Ed25519Signature2018(JwsLinkedDataSignature):
    def __init__(
        self,
        verification_method: str,
        proof: dict = None,
        date: Union[datetime, str] = None,
    ):
        super().__init__(
            signature_type="Ed25519Signature",
            algorithm="EdDSA",
            key_pair=Ed25519KeyPair,
            verification_method=verification_method,
            proof=proof,
            date=date,
        )
        self.required_key_type = "Ed25519VerificationKey2018"
