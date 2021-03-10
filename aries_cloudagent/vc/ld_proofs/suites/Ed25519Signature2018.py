from datetime import datetime
from typing import Union

from ..crypto import Ed25519WalletKeyPair, Ed25519KeyPair
from .JwsLinkedDataSignature import JwsLinkedDataSignature


class Ed25519Signature2018(JwsLinkedDataSignature):
    def __init__(
        self,
        verification_method: str,
        key_pair: Union[Ed25519WalletKeyPair, Ed25519KeyPair],
        proof: dict = None,
        date: Union[datetime, str] = None,
    ):
        super().__init__(
            signature_type="Ed25519Signature2018",
            algorithm="EdDSA",
            key_pair=key_pair,
            verification_method=verification_method,
            proof=proof,
            date=date,
        )
        self.required_key_type = "Ed25519VerificationKey2018"
