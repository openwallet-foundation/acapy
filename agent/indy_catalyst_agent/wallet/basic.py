"""
In-memory implementation of BaseWallet interface
"""

from typing import Sequence

from .base import BaseWallet, DIDInfo, PairwiseInfo
from .crypto import (
    create_keypair, random_seed, validate_seed,
    sign_message, verify_signed_message,
    encode_pack_message, decode_pack_message,
)
from .error import WalletException, WalletDuplicateException, WalletNotFoundException
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
        Check whether wallet is currently open
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

    async def create_local_did(
            self,
            seed: str = None,
            did: str = None,
            metadata: dict = None) -> DIDInfo:
        """
        Create and store a new local DID
        """
        seed = validate_seed(seed) or random_seed()
        verkey, secret = create_keypair(seed)
        if not did:
            did = bytes_to_b58(verkey[:16])
        if did in self._local_dids:
            raise WalletDuplicateException("DID already exists in wallet")
        verkey_enc = bytes_to_b58(verkey)
        self._local_dids[did] = {
            "seed": seed,
            "secret": secret,
            "verkey": verkey_enc,
            "metadata": metadata.copy() if metadata else {},
        }
        return DIDInfo(did, verkey_enc, self._local_dids[did]["metadata"].copy())

    def _get_did_info(self, did: str) -> DIDInfo:
        """
        Convert internal DID record to DIDInfo
        """
        info = self._local_dids[did]
        return DIDInfo(
            did=did,
            verkey=info["verkey"],
            metadata=info["metadata"].copy(),
        )

    async def get_local_dids(self) -> Sequence[DIDInfo]:
        """
        Get list of defined local DIDs
        """
        ret = [self._get_did_info(did) for did in self._local_dids]
        return ret

    async def get_local_did(self, did: str) -> DIDInfo:
        """
        Find info for a local DID
        """
        if did not in self._local_dids:
            raise WalletNotFoundException("DID not found: {}".format(did))
        return self._get_did_info(did)

    async def get_local_did_for_verkey(self, verkey: str) -> DIDInfo:
        """
        Resolve a local DID from a verkey
        """
        for did, info in self._local_dids.items():
            if info["verkey"] == verkey:
                return self._get_did_info(did)
        raise WalletNotFoundException("Verkey not found: {}".format(verkey))

    async def replace_local_did_metadata(self, did: str, metadata: dict):
        """
        Replace metadata for a local DID
        """
        if did not in self._local_dids:
            raise WalletNotFoundException("Unknown DID: {}".format(did))
        self._local_dids[did]["metadata"] = metadata.copy() if metadata else {}

    async def create_pairwise(
            self,
            their_did: str,
            their_verkey: str,
            my_did: str = None,
            metadata: dict = None) -> PairwiseInfo:
        """
        Create a new pairwise DID for a secure connection
        """
        if my_did:
            my_info = await self.get_local_did(my_did)
        else:
            my_info = await self.create_local_did(None, None, {"pairwise_for": their_did})

        if their_did in self._pair_dids:
            raise WalletDuplicateException(
                    "Pairwise DID already present in wallet: {}".format(their_did))

        self._pair_dids[their_did] = {
            "my_did": my_info.did,
            "their_verkey": their_verkey,
            "metadata": metadata.copy() if metadata else {},
        }
        return self._get_pairwise_info(their_did)

    def _get_pairwise_info(self, their_did: str) -> PairwiseInfo:
        """
        Convert internal pairwise DID record to PairwiseInfo
        """
        info = self._pair_dids[their_did]
        return PairwiseInfo(
            their_did=their_did,
            their_verkey=info["their_verkey"],
            my_did=info["my_did"],
            my_verkey=self._local_dids[info["my_did"]]["verkey"],
            metadata=info["metadata"].copy(),
        )

    async def get_pairwise_list(self) -> Sequence[PairwiseInfo]:
        """
        Get list of defined pairwise DIDs
        """
        ret = [self._get_pairwise_info(their_did) for their_did in self._pair_dids]
        return ret

    async def get_pairwise_for_did(self, their_did: str) -> PairwiseInfo:
        """
        Find info for a pairwise DID
        """
        if their_did not in self._pair_dids:
            raise WalletNotFoundException("Unknown target DID: {}".format(their_did))
        return self._get_pairwise_info(their_did)

    async def get_pairwise_for_verkey(self, their_verkey: str) -> PairwiseInfo:
        """
        Resolve a pairwise DID from a verkey
        """
        for did, info in self._pair_dids.items():
            if info["their_verkey"] == their_verkey:
                return self._get_pairwise_info(did)
        raise WalletNotFoundException("Verkey not found: {}".format(their_verkey))

    async def replace_pairwise_metadata(self, their_did: str, metadata: dict):
        """
        Replace metadata for a pairwise DID
        """
        if their_did not in self._pair_dids:
            raise WalletNotFoundException("Unknown target DID: {}".format(their_did))
        self._pair_dids[their_did]["metadata"] = metadata.copy() if metadata else {}

    def _get_private_key(self, verkey: str, long=False):
        """
        Resolve private key for a wallet DID
        """
        for info in self._local_dids.values():
            if info["verkey"] == verkey:
                return info["secret"] if long else info["seed"]
        return None

    async def sign_message(self, message: bytes, from_verkey: str) -> bytes:
        """
        Sign a message using the private key associated with a given verkey
        """
        if not message:
            raise WalletException("Message not provided")
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

    async def pack_message(self, message: str, to_verkeys: Sequence[str], from_verkey: str = None) \
            -> bytes:
        """
        Pack a message for one or more recipients
        """
        keys_bin = [b58_to_bytes(key) for key in to_verkeys]
        if from_verkey:
            secret = self._get_private_key(from_verkey)
            if not secret:
                raise WalletNotFoundException(
                    "Private key not found for verkey: {}".format(from_verkey))
        else:
            secret = None

        result = encode_pack_message(message, keys_bin, secret)
        return result

    async def unpack_message(self, enc_message: bytes) -> (str, str, str):
        """
        Unpack a message
        """
        if not enc_message:
            raise WalletException("Message not provided")
        try:
            message, from_verkey, to_verkey = \
                decode_pack_message(enc_message, lambda k: self._get_private_key(k, True))
        except ValueError as e:
            raise WalletException("Message could not be unpacked: {}".format(str(e)))
        return message, from_verkey, to_verkey
