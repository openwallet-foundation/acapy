"""Key pair based on base wallet interface."""

from typing import List, Optional, Union

from base58 import b58encode

from ....core.profile import Profile
from ....utils.multiformats import multibase, multicodec
from ....wallet.base import BaseWallet
from ....wallet.key_type import KeyType
from ....wallet.util import b58_to_bytes
from ..error import LinkedDataProofException
from .key_pair import KeyPair


class WalletKeyPair(KeyPair):
    """Base wallet key pair."""

    def __init__(
        self,
        *,
        profile: Profile,
        key_type: KeyType,
        public_key_base58: Optional[str] = None,
    ) -> None:
        """Initialize new WalletKeyPair instance."""
        super().__init__()
        self.profile = profile
        self.key_type = key_type
        self.public_key_base58 = public_key_base58

    async def sign(self, message: Union[List[bytes], bytes]) -> bytes:
        """Sign message using wallet."""
        if not self.public_key_base58:
            raise LinkedDataProofException(
                "Unable to sign message with WalletKey: No key to sign with"
            )
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            return await wallet.sign_message(
                message=message,
                from_verkey=self.public_key_base58,
            )

    async def verify(self, message: Union[List[bytes], bytes], signature: bytes) -> bool:
        """Verify message against signature using wallet."""
        if not self.public_key_base58:
            raise LinkedDataProofException(
                "Unable to verify message with key pair: No key to verify with"
            )

        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            return await wallet.verify_message(
                message=message,
                signature=signature,
                from_verkey=self.public_key_base58,
                key_type=self.key_type,
            )

    def from_verification_method(self, verification_method: dict) -> "WalletKeyPair":
        """Create new WalletKeyPair from public key in verification method."""
        if "publicKeyBase58" in verification_method:
            key_material = verification_method["publicKeyBase58"]
        elif "sec:publicKeyMultibase" in verification_method:
            # verification_method is framed
            _, raw_key = multicodec.unwrap(
                multibase.decode(verification_method["sec:publicKeyMultibase"]["@value"])
            )
            key_material = b58encode(raw_key).decode()
        else:
            raise LinkedDataProofException(
                f"Unrecognized verification method type: {verification_method}"
            )

        return WalletKeyPair(
            profile=self.profile,
            key_type=self.key_type,
            public_key_base58=key_material,
        )

    @property
    def public_key(self) -> Optional[bytes]:
        """Getter for public key."""
        return b58_to_bytes(self.public_key_base58)

    @property
    def has_public_key(self) -> bool:
        """Whether key pair has public key."""
        return self.public_key_base58 is not None
