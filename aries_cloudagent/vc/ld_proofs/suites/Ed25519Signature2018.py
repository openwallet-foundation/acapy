from datetime import datetime
from typing import Union

from ..crypto import Ed25519WalletKeyPair
from .JwsLinkedDataSignature import JwsLinkedDataSignature


class Ed25519Signature2018(JwsLinkedDataSignature):
    def __init__(
        self,
        verification_method: str,
        key_pair: Ed25519WalletKeyPair,
        proof: dict = None,
        date: Union[datetime, str] = None,
    ):
        super().__init__(
            signature_type="Ed25519Signature2018",
            algorithm="EdDSA",
            required_key_type="Ed25519VerificationKey2018",
            key_pair=key_pair,
            verification_method=verification_method,
            proof=proof,
            date=date,
        )
