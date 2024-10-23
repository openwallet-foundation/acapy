"""DID manager for Indy."""

from typing import Optional

from aries_askar import AskarError, Key, KeyAlg

from ...core.profile import Profile
from ...wallet.askar import CATEGORY_DID
from ...wallet.crypto import validate_seed
from ...wallet.did_method import INDY, DIDMethods
from ...wallet.did_parameters_validation import DIDParametersValidation
from ...wallet.error import WalletError
from ...wallet.key_type import ED25519
from ...wallet.util import bytes_to_b58


class DidIndyManager:
    """DID manager for Indy."""

    def __init__(self, profile: Profile) -> None:
        """Initialize the DID  manager."""
        self.profile = profile

    def _create_key_pair(self, seed: Optional[str] = None) -> Key:
        if seed and not self.profile.settings.get("wallet.allow_insecure_seed"):
            raise WalletError("Insecure seed is not allowed")
        if seed:
            seed = validate_seed(seed)
            return Key.from_secret_bytes(KeyAlg.ED25519, seed)
        return Key.generate(KeyAlg.ED25519)

    async def register(self, seed: Optional[str] = None) -> dict:
        """Register a DID Indy."""
        did_validation = DIDParametersValidation(self.profile.inject(DIDMethods))
        key_pair = self._create_key_pair(seed)
        verkey_bytes = key_pair.get_public_bytes()
        verkey = bytes_to_b58(verkey_bytes)

        did = f"did:indy:{did_validation.validate_or_derive_did(INDY, ED25519, verkey_bytes, None)}"  # noqa: E501

        async with self.profile.session() as session:
            try:
                await session.handle.insert_key(verkey, key_pair)
                await session.handle.insert(
                    CATEGORY_DID,
                    did,
                    value_json={
                        "did": did,
                        "method": INDY.method_name,
                        "verkey": verkey,
                        "verkey_type": ED25519.key_type,
                        "metadata": {},
                    },
                    tags={
                        "method": INDY.method_name,
                        "verkey": verkey,
                        "verkey_type": ED25519.key_type,
                    },
                )
            except AskarError as err:
                raise WalletError(f"Error registering DID: {err}") from err
        return {
            "did": did,
            "verkey": verkey,
        }
