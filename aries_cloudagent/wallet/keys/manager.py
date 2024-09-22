"""Multikey class."""

from ...core.profile import Profile
from ..base import BaseWallet
from ..key_type import ED25519
from ..util import b58_to_bytes, bytes_to_b58
from ...utils.multiformats import multibase
from ...wallet.error import WalletNotFoundError
from ..did_method import KEY
from ...admin.request_context import AdminRequestContext

ALG_MAPPINGS = {
    "ed25519": {"key_type": ED25519, "prefix_hex": "ed01", "prefix_lenght": 2}
}

def multikey_to_verkey(multikey, alg="ed25519"):
    """Transform multikey to verkey."""
    try:
        prefix_lenght = ALG_MAPPINGS[alg]["prefix_lenght"]
        public_bytes = bytes(bytearray(multibase.decode(multikey))[prefix_lenght:])
        return bytes_to_b58(public_bytes)
    except:
        raise MultikeyManagerError(f"Invalid multikey value {multikey} for algorithm {alg}.")


def verkey_to_multikey(verkey, alg="ed25519"):
    """Transform verkey to multikey."""
    try:
        prefix_hex = ALG_MAPPINGS[alg]["prefix_hex"]
        prefixed_key_hex = f"{prefix_hex}{b58_to_bytes(verkey).hex()}"
        return multibase.encode(bytes.fromhex(prefixed_key_hex), "base58btc")
    except:
        raise MultikeyManagerError(f"Invalid verkey value {verkey} for algorithm {alg}.")


async def kid_exists(wallet, kid):
    """Check if kid exists."""
    try:
        if await wallet.get_key_by_kid(kid=kid):
            return True
    except WalletNotFoundError:
        return False


class MultikeyManagerError(Exception):
    """Generic MultikeyManager Error."""


class MultikeyManager:
    """Class for managing wallet keys."""

    def __init__(self, context=AdminRequestContext):
        """Initialize the MultikeyManager."""
        self.context = context

    def _multikey_to_verkey(self, multikey, alg="ed25519"):
        """Transform multikey to verkey."""
        prefix_lenght = ALG_MAPPINGS[alg]["prefix_lenght"]
        public_bytes = bytes(bytearray(multibase.decode(multikey))[prefix_lenght:])
        return bytes_to_b58(public_bytes)

    def _verkey_to_multikey(self, verkey, alg="ed25519"):
        """Transform verkey to multikey."""
        prefix_hex = ALG_MAPPINGS[alg]["prefix_hex"]
        prefixed_key_hex = f"{prefix_hex}{b58_to_bytes(verkey).hex()}"
        return multibase.encode(bytes.fromhex(prefixed_key_hex), "base58btc")

    async def kid_exists(self, wallet, kid):
        """Check if kid exists."""
        try:
            if await wallet.get_key_by_kid(kid=kid):
                return True
        except (WalletNotFoundError, AttributeError):
            return False

    async def from_kid(self, kid: str):
        """Fetch a single key."""
        async with self.context.session() as session:
            wallet: BaseWallet | None = session.inject_or(BaseWallet)
            key_info = await wallet.get_key_by_kid(kid=kid)
            return {
                "kid": key_info.kid,
                "multikey": self._verkey_to_multikey(key_info.verkey),
            }

    async def from_multikey(self, multikey: str):
        """Fetch a single key."""
        async with self.context.session() as session:
            wallet: BaseWallet | None = session.inject_or(BaseWallet)
            key_info = await wallet.get_signing_key(
                verkey=self._multikey_to_verkey(multikey)
            )
            return {
                "kid": key_info.kid,
                "multikey": self._verkey_to_multikey(key_info.verkey),
            }

    async def create(self, seed=None, kid=None, alg="ed25519"):
        """Create a new key pair."""
        
        if seed and not self.context.settings.get("wallet.allow_insecure_seed"):
            raise MultikeyManagerError("Seed support is not enabled.")

        if alg not in ALG_MAPPINGS:
            raise MultikeyManagerError(
                f"Unknown key algorithm, use one of {[mapping for mapping in ALG_MAPPINGS]}."
            )

        async with self.context.session() as session:
            wallet: BaseWallet | None = session.inject_or(BaseWallet)

            if kid and await self.kid_exists(wallet=wallet, kid=kid):
                raise MultikeyManagerError(
                    f"kid '{kid}' already exists in wallet."
                )

            key_type = ALG_MAPPINGS[alg]["key_type"]
            key_info = await wallet.create_key(key_type=key_type, seed=seed, kid=kid)
            # did_info = await wallet.create_local_did(method=KEY, key_type=key_type, seed=seed)
            # if kid:
            #     key_info = await wallet.assign_kid_to_key(verkey=did_info.verkey, kid=kid)
            return {
                "kid": key_info.kid,
                "multikey": self._verkey_to_multikey(key_info.verkey),
            }

    async def update(self, multikey: str, kid: str):
        """Assign a new kid to a key pair."""

        async with self.context.session() as session:
            wallet: BaseWallet | None = session.inject_or(BaseWallet)

            if kid and await self.kid_exists(wallet=wallet, kid=kid):
                raise MultikeyManagerError(
                    f"kid '{kid}' already exists in wallet."
                )
            key_info = await wallet.assign_kid_to_key(
                verkey=self._multikey_to_verkey(multikey), 
                kid=kid
            )
            return {
                "kid": key_info.kid,
                "multikey": self._verkey_to_multikey(key_info.verkey),
            }
