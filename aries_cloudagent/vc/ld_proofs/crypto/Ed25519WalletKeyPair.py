"""Ed25519 key pair based on base wallet interface."""

from typing import Optional

from ....wallet.util import b58_to_bytes
from ....wallet.base import BaseWallet
from ..error import LinkedDataProofException
from .WalletKeyPair import WalletKeyPair


class Ed25519WalletKeyPair(WalletKeyPair):
    """Ed25519 wallet key pair."""

    # TODO: maybe make public key buffer default input?
    # This way we can make it an input on the lower level key pair class
    def __init__(self, *, wallet: BaseWallet, public_key_base58: Optional[str] = None):
        """Initialize new Ed25519WalletKeyPair instance."""
        super().__init__(wallet=wallet)

        self.public_key_base58 = public_key_base58

    async def sign(self, message: bytes) -> bytes:
        """Sign message using Ed25519 key."""
        if not self.public_key_base58:
            raise LinkedDataProofException(
                "Unable to sign message with Ed25519WalletKeyPair: No key to sign with"
            )
        return await self.wallet.sign_message(
            message,
            self.public_key_base58,
        )

    async def verify(self, message: bytes, signature: bytes) -> bool:
        """Verify message against signature using Ed25519 key."""
        if not self.public_key_base58:
            raise LinkedDataProofException(
                "Unable to verify message with Ed25519WalletKeyPair"
                ": No key to verify with"
            )

        return await self.wallet.verify_message(
            message, signature, self.public_key_base58
        )

    def from_verification_method(
        self, verification_method: dict
    ) -> "Ed25519WalletKeyPair":
        """Create new Ed25519WalletKeyPair from public key in verification method."""
        if "publicKeyBase58" not in verification_method:
            raise LinkedDataProofException(
                "Unable to set public key from verification method: no publicKeyBase58"
            )

        return Ed25519WalletKeyPair(
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
