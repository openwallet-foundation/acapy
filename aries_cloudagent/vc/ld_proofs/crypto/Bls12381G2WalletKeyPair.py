"""Bls12381G2 key pair based on base wallet interface."""

from typing import List, Optional, Union

from ....wallet.util import b58_to_bytes
from ....wallet.base import BaseWallet
from ....wallet.crypto import KeyType
from ..error import LinkedDataProofException
from .WalletKeyPair import WalletKeyPair


class Bls12381G2WalletKeyPair(WalletKeyPair):
    """Bls12381G2 wallet key pair."""

    def __init__(self, *, wallet: BaseWallet, public_key_base58: Optional[str] = None):
        """Initialize new Bls12381G2WalletKeyPair instance."""
        super().__init__(wallet=wallet)

        self.public_key_base58 = public_key_base58

    async def sign(self, messages: Union[List[bytes], bytes]) -> bytes:
        """Sign message using Bls12381G2 key."""
        if not self.public_key_base58:
            raise LinkedDataProofException(
                "Unable to sign message with Bls12381G2WalletKeyPair: No key to sign with"
            )

        return await self.wallet.sign_message(
            message=messages,
            from_verkey=self.public_key_base58,
        )

    async def verify(
        self, messages: Union[List[bytes], bytes], signature: bytes
    ) -> bool:
        """Verify message against signature using Bls12381G2 key."""
        if not self.public_key_base58:
            raise LinkedDataProofException(
                "Unable to verify message with Bls12381G2WalletKeyPair"
                ": No key to verify with"
            )

        return await self.wallet.verify_message(
            message=messages,
            signature=signature,
            from_verkey=self.public_key_base58,
            key_type=KeyType.BLS12381G2,
        )

    def from_verification_method(
        self, verification_method: dict
    ) -> "Bls12381G2WalletKeyPair":
        """Create new Bls12381G2WalletKeyPair from public key in verification method."""
        if "publicKeyBase58" not in verification_method:
            raise LinkedDataProofException(
                "Unable to set public key from verification method: no publicKeyBase58"
            )

        return Bls12381G2WalletKeyPair(
            wallet=self.wallet, public_key_base58=verification_method["publicKeyBase58"]
        )

    @property
    def public_key(self) -> Optional[bytes]:
        """Getter for public key."""
        return b58_to_bytes(self.public_key_base58)

    @property
    def has_public_key(self) -> bool:
        """Whether key pair has public key."""
        return self.public_key_base58 is not None
