"""Multikey class."""

from ...core.profile import ProfileSession
from ..base import BaseWallet
from ..key_type import ED25519
from ..util import b58_to_bytes, bytes_to_b58
from ...utils.multiformats import multibase
from ...wallet.error import WalletNotFoundError

DEFAULT_ALG = "ed25519"
ALG_MAPPINGS = {
    "ed25519": {"key_type": ED25519, "prefix_hex": "ed01", "prefix_length": 2}
}


class MultikeyManagerError(Exception):
    """Generic MultikeyManager Error."""


class MultikeyManager:
    """Class for managing wallet keys."""

    def __init__(self, session: ProfileSession):
        """Initialize the MultikeyManager."""

        self.wallet: BaseWallet = session.inject(BaseWallet)

    def _multikey_to_verkey(self, multikey: str, alg: str = DEFAULT_ALG):
        """Transform multikey to verkey."""

        prefix_length = ALG_MAPPINGS[alg]["prefix_length"]
        public_bytes = bytes(bytearray(multibase.decode(multikey))[prefix_length:])

        return bytes_to_b58(public_bytes)

    def _verkey_to_multikey(self, verkey: str, alg: str = DEFAULT_ALG):
        """Transform verkey to multikey."""

        prefix_hex = ALG_MAPPINGS[alg]["prefix_hex"]
        prefixed_key_hex = f"{prefix_hex}{b58_to_bytes(verkey).hex()}"

        return multibase.encode(bytes.fromhex(prefixed_key_hex), "base58btc")

    async def kid_exists(self, kid: str):
        """Check if kid exists."""

        try:
            key = await self.wallet.get_key_by_kid(kid=kid)

            if key:
                return True

        except (WalletNotFoundError, AttributeError):
            return False

    async def from_kid(self, kid: str):
        """Fetch a single key."""

        key_info = await self.wallet.get_key_by_kid(kid=kid)

        return {
            "kid": key_info.kid,
            "multikey": self._verkey_to_multikey(key_info.verkey),
        }

    async def from_multikey(self, multikey: str):
        """Fetch a single key."""

        key_info = await self.wallet.get_signing_key(
            verkey=self._multikey_to_verkey(multikey)
        )

        return {
            "kid": key_info.kid,
            "multikey": self._verkey_to_multikey(key_info.verkey),
        }

    async def create(self, seed: str = None, kid: str = None, alg: str = DEFAULT_ALG):
        """Create a new key pair."""

        if alg not in ALG_MAPPINGS:
            raise MultikeyManagerError(
                f"Unknown key algorithm, use one of {list(ALG_MAPPINGS.keys())}."
            )

        if kid and await self.kid_exists(kid=kid):
            raise MultikeyManagerError(f"kid '{kid}' already exists in wallet.")

        key_type = ALG_MAPPINGS[alg]["key_type"]
        key_info = await self.wallet.create_key(key_type=key_type, seed=seed, kid=kid)

        return {
            "kid": key_info.kid,
            "multikey": self._verkey_to_multikey(key_info.verkey),
        }

    async def update(self, multikey: str, kid: str):
        """Assign a new kid to a key pair."""

        if kid and await self.kid_exists(kid=kid):
            raise MultikeyManagerError(f"kid '{kid}' already exists in wallet.")

        key_info = await self.wallet.assign_kid_to_key(
            verkey=self._multikey_to_verkey(multikey), kid=kid
        )

        return {
            "kid": key_info.kid,
            "multikey": self._verkey_to_multikey(key_info.verkey),
        }
