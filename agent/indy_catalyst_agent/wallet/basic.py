"""
In-memory implementation of BaseWallet interface
"""

from typing import Sequence

from .base import BaseWallet
from .crypto import (
    create_keypair, random_seed, sign_message, verify_signed_message,
    encode_pack_message, decode_pack_message,
)
from .error import WalletException
from .util import b58_to_bytes, bytes_to_b58, b64_to_bytes


class BasicWallet(BaseWallet):
    """
    In-memory wallet implementation
    """

    def __init__(self, config: dict = None):
        if not config:
            config = {}
        super(BasicWallet, self).__init__(config)
        self._name = config.get("name")
        self._local_dids = {}
        self._pair_dids = {}

    @property
    def opened(self) -> bool:
        """
        Get internal wallet reference
        """
        return True

    async def open(self):
        """
        Does not apply to in-memory wallet
        """
        pass

    async def close(self):
        """
        Does not apply to in-memory wallet
        """
        pass

    async def create_local_did(self, seed: str = None, did: str = None, metadata: dict = None) -> str:
        """
        Create and store a new local DID
        """
        if not seed:
            seed = random_seed()
        else:
            if "=" in seed:
                seed = b64_to_bytes(seed)
            if isinstance(seed, str):
                seed = seed.encode("ascii")
            if len(seed) != 32:
                raise WalletException("Seed must be 32 bytes in length")
        verkey, secret = create_keypair(seed)
        if not did:
            did = bytes_to_b58(verkey[:16])
        self._local_dids[did] = {
            "seed": seed,
            "secret": secret,
            "verkey": verkey,
            "verkey_enc": bytes_to_b58(verkey),
            "metadata": metadata.copy() if metadata else {},
        }
        return did

    async def get_local_verkey_for_did(self, did: str) -> str:
        """
        Resolve a local verkey from a DID
        """
        if did not in self._local_dids:
            raise WalletException("DID not found: {}".format(did))
        return self._local_dids[did]["verkey_enc"]

    async def get_local_did_for_verkey(self, verkey: str) -> str:
        """
        Resolve a local DID from a verkey
        """
        for did, info in self._local_dids.items():
            if info["verkey"] == verkey:
                return did
        raise WalletException("Verkey not found: {}".format(verkey))

    async def get_local_did_metadata(self, did: str) -> dict:
        """
        Get metadata for a local DID
        """
        if did not in self._local_dids:
            raise WalletException("Unknown DID: {}".format(did))
        return self._local_dids[did]["metadata"]

    async def replace_local_did_metadata(self, did: str, metadata: dict):
        """
        Replace metadata for a local DID
        """
        if did not in self._local_dids:
            raise WalletException("Unknown DID: {}".format(did))
        self._local_dids[did]["metadata"] = metadata.copy() if metadata else {}

    async def create_pairwise_did(self, to_did: str, from_did: str, metadata: dict = None) -> str:
        """
        Create a new pairwise DID for a secure connection
        """
        pass

    async def get_pairwise_did_for_verkey(self, verkey: str) -> str:
        """
        Resolve a pairwise DID from a verkey
        """
        pass

    async def get_pairwise_did_metadata(self, did: str) -> dict:
        """
        Get metadata for a pairwise DID
        """
        pass

    async def replace_pairwise_did_metadata(self, did: str, metadata: dict):
        """
        Replace metadata for a pairwise DID
        """
        pass

    def _get_private_key(self, verkey: str, long=False):
        """
        Resolve private key for a wallet DID
        """
        for info in self._local_dids.values():
            if info["verkey_enc"] == verkey:
                return info["secret"] if long else info["seed"]
        for info in self._pair_dids.values():
            if info["verkey_enc"] == verkey:
                return info["secret"] if long else info["seed"]
        return None

    async def sign_message(self, message: bytes, from_verkey: str) -> bytes:
        """
        Sign a message using the private key associated with a given verkey
        """
        if not from_verkey:
            raise WalletException("Verkey not provided")
        secret = self._get_private_key(from_verkey, True)
        if not secret:
            raise WalletException("Private key not found for verkey: {}".format(from_verkey))
        signature = sign_message(message, secret)
        return signature

    async def verify_message(self, message: bytes, signature: bytes, from_verkey: str) -> bool:
        """
        Verify a signature against the public key of the signer
        """
        if not from_verkey:
            raise WalletException("Verkey not provided")
        if not signature:
            raise WalletException("Signature not provided")
        if not message:
            raise WalletException("Message not provided")
        verkey_bytes = b58_to_bytes(from_verkey)
        verified = verify_signed_message(signature + message, verkey_bytes)
        return verified

    async def pack_message(self, message: str, to_verkeys: Sequence[str], from_verkey: str = None) -> bytes:
        """
        Pack a message for one or more recipients
        """
        keys_bin = [b58_to_bytes(key) for key in to_verkeys]
        if from_verkey:
            secret = self._get_private_key(from_verkey)
            if not secret:
                raise WalletException("Private key not found for verkey: {}".format(from_verkey))
        else:
            secret = None

        result = encode_pack_message(message, keys_bin, secret)
        return result

    async def unpack_message(self, enc_message: bytes) -> (str, str):
        """
        Unpack a message
        """
        if not enc_message:
            raise WalletException("Message not provided")
        try:
            message, from_verkey, _to_verkey = \
                decode_pack_message(enc_message, lambda k: self._get_private_key(k, True))
        except ValueError as e:
            raise WalletException("Message could not be unpacked: {}".format(str(e)))
        return message, from_verkey
