"""Multikey class."""

from ...core.profile import Profile
from ..base import BaseWallet
from ..key_type import ED25519
from ..util import b58_to_bytes, bytes_to_b58
from ..key_type import KeyTypes, KeyType
from ...utils.multiformats import multibase
import json

KEY_MAPPINGS = {"ed25519": ED25519}
PREFIX_MAPPINGS = {"ed25519": "ed01"}
PREFIX_LENGHTS = {"ed25519": 2}


class MultikeyManagerError(Exception):
    """Generic MultikeyManager Error."""


class MultikeyManager:
    """Class for managing wallet keys."""

    def __init__(self, profile=Profile):
        """Initialize the MultikeyManager."""
        self.profile = profile

    def _multikey_to_verkey(self, multikey, alg="ed25519"):
        public_bytes = bytes(bytearray(multibase.decode(multikey))[PREFIX_LENGHTS[alg]:])
        return bytes_to_b58(public_bytes)

    def _verkey_to_multikey(self, verkey, alg="ed25519"):
        prefixed_key_hex = f"{PREFIX_MAPPINGS[alg]}{b58_to_bytes(verkey).hex()}"
        return multibase.encode(bytes.fromhex(prefixed_key_hex), "base58btc")

    async def from_kid(self, kid: str):
        """Fetch a single key."""
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            key_info = await wallet.get_key_by_kid(kid=kid)
            return self._verkey_to_multikey(key_info['verkey'])

    async def from_multikey(self, multikey: str):
        """Fetch a single key."""
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            verkey = self._multikey_to_verkey(multikey)
            key_info = await wallet.get_signing_key(verkey=verkey)
            return self._verkey_to_multikey(key_info['verkey'])

    async def create(self, seed=None, kid=None, alg="ed25519"):
        """Create a new key pair."""
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            try:
                if kid and await wallet.get_key_by_kid(kid=kid):
                    raise MultikeyManagerError(
                        f"Verification Method {kid} is already bound to a key pair."
                    )
            except:
                pass
            key_info = await wallet.create_key(
                key_type=KEY_MAPPINGS[alg], seed=seed, kid=kid
            )
            return self._verkey_to_multikey(key_info.verkey)

    async def update(self, multikey: str, kid: str):
        """Assign a new kid to a key pair."""
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            verkey = self._multikey_to_verkey(multikey)
            try:
                if await wallet.get_key_by_kid(kid=kid):
                    raise MultikeyManagerError(
                        f"Verification Method {kid} is already bound to a key pair."
                    )
            except:
                pass
            key_info = await wallet.assign_kid_to_key(
                verkey=verkey, kid=kid
            )
            return self._verkey_to_multikey(key_info.verkey)
