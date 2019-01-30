"""
Indy implementation of BaseWallet interface
"""

import json
from typing import Sequence

import indy.did
import indy.crypto
import indy.pairwise
from indy.error import IndyError, ErrorCode
from von_anchor.error import ExtantWallet
from von_anchor.wallet import Wallet as AnchorWallet

from .base import BaseWallet, DIDInfo
from .crypto import (
    create_keypair, random_seed, validate_seed,
)
from .error import WalletException, WalletNotFoundException
from .util import b58_to_bytes, bytes_to_b58, b64_to_bytes, bytes_to_b64


class IndyWallet(BaseWallet):
    """
    Indy wallet implementation
    """

    DEFAULT_FRESHNESS = 0
    DEFAULT_KEY = ""
    DEFAULT_NAME = "default"
    DEFAULT_STORAGE_TYPE = None

    def __init__(self, config: dict = None):
        if not config:
            config = {}
        super(IndyWallet, self).__init__(config)
        self._auto_create = config.get("auto_create", True)
        self._auto_remove = config.get("auto_remove", False)
        self._freshness_time = config.get("freshness_time", False)
        self._instance = None
        self._key = config.get("key") or self.DEFAULT_KEY
        self._name = config.get("name") or self.DEFAULT_NAME
        self._seed = validate_seed(config.get("seed"))
        self._storage_type = config.get("storage_type") or self.DEFAULT_STORAGE_TYPE

    @property
    def handle(self):
        """
        Get internal wallet reference
        """
        return self._instance and self._instance.handle

    @property
    def opened(self) -> bool:
        """
        Check whether wallet is currently open
        """
        return bool(self._instance)

    @property
    def _wallet_config(self) -> dict:
        return {
            "id": self._name,
            "freshness_time": self._freshness_time,
            "storage_type": self._storage_type,
        }

    @property
    def _wallet_access(self) -> dict:
        return {
            "key": self._key,
            # key_derivation_method
            # storage_credentials
        }

    async def _create(self, seed = None, replace: bool = False) -> bool:
        """
        Create the wallet instance
        """
        if seed:
            self._seed = validate_seed(seed)
        if not self._seed:
            self._seed = random_seed()

        if replace:
            await self._instance.remove()
        try:
            await self._instance.create(bytes_to_b64(self._seed))
        except ExtantWallet as e:
            if replace:
                raise WalletException("Wallet was not removed by SDK, may still be open") from e
            return False
        return True

    async def open(self):
        """
        Open wallet, removing and/or creating it if so configured
        """
        if self.opened:
            return

        self._instance = AnchorWallet(
            self._name,
            self._storage_type,
            self._wallet_config,
            self._wallet_access,
        )

        if self._auto_create:
            await self._create(None, self._auto_remove)

        await self._instance.open()

    async def close(self):
        """
        Close previously-opened wallet, removing it if so configured
        """
        if self._instance:
            await self._instance.close()
            if self._auto_remove:
                await self._instance.remove()
            self._instance = None

    async def get_local_dids(self) -> Sequence[DIDInfo]:
        """
        Get list of defined local DIDs
        """
        ret = []
        dids_json = await indy.did.list_my_dids_with_meta(self.handle)
        dids = json.loads(dids_json)
        for info in dids:
            ret.append(
                DIDInfo(
                    did=info["did"],
                    verkey=info["verkey"],
                    tempVerkey=info["tempVerkey"],
                    metadata=info["metadata"],
                )
            )
        return ret

    async def create_local_did(self, seed: str = None, did: str = None, metadata: dict = None) -> str:
        """
        Create and store a new local DID
        """
        cfg =  {}
        if seed:
            cfg["seed"] = bytes_to_b64(validate_seed(seed))
        if did:
            cfg["did"] = did
        did_json = json.dumps(cfg)
        # crypto_type, cid - optional parameters skipped
        did, verkey = await indy.did.create_and_store_my_did(self.handle, did_json)
        if metadata:
            await self.replace_local_did_metadata(did, metadata)
        return did

    async def get_local_verkey_for_did(self, did: str) -> str:
        """
        Resolve a local verkey from a DID
        """
        try:
            verkey = await indy.did.key_for_local_did(self.handle, did)
        except IndyError as x_indy:
            if x_indy.error_code == ErrorCode.WalletItemNotFound:
                raise WalletNotFoundException("Unknown DID: {}".format(did))
            else:
                raise WalletException(str(x_indy))
        return verkey

    async def get_local_did_for_verkey(self, verkey: str) -> str:
        """
        Resolve a local DID from a verkey
        """
        dids = await self.get_local_dids()
        for info in dids:
            if info.verkey == verkey:
                return info.did
        raise WalletNotFoundException("No DID defined for verkey: {}".format(verkey))

    async def get_local_did_metadata(self, did: str) -> dict:
        """
        Get metadata for a local DID
        """
        try:
            meta = await indy.did.get_did_metadata(self.handle, did)
        except IndyError as x_indy:
            if x_indy.error_code == ErrorCode.WalletItemNotFound:
                raise WalletNotFoundException("Unknown DID: {}".format(did))
            else:
                raise WalletException(str(x_indy))
        return json.loads(meta) if meta else {}

    async def replace_local_did_metadata(self, did: str, metadata: dict):
        """
        Replace metadata for a local DID
        """
        meta_json = json.dumps(metadata or {})
        await self.get_local_verkey_for_did(did) # throw exception if undefined
        await indy.did.set_did_metadata(self.handle, did, meta_json)

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

    async def sign_message(self, message: bytes, from_verkey: str) -> bytes:
        """
        Sign a message using the private key associated with a given verkey
        """
        if not message:
            raise WalletException("Message not provided")
        if not from_verkey:
            raise WalletException("Verkey not provided")
        result = await indy.crypto.crypto_sign(self.handle, from_verkey, message)
        return result

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
        result = await indy.crypto.crypto_verify(from_verkey, message, signature)
        return result

    async def pack_message(self, message: str, to_verkeys: Sequence[str], from_verkey: str = None) -> bytes:
        """
        Pack a message for one or more recipients
        """
        if message is None:
            raise WalletException("Message not provided")
        result = await indy.crypto.pack_message(
            self.handle,
            message,
            to_verkeys,
            from_verkey)
        return result

    async def unpack_message(self, enc_message: bytes) -> (str, str, str):
        """
        Unpack a message
        """
        if not enc_message:
            raise WalletException("Message not provided")
        unpacked_json = await indy.crypto.unpack_message(
            self.handle,
            enc_message)
        unpacked = json.loads(unpacked_json)
        message = unpacked["message"]
        to_verkey = unpacked.get("recipient_verkey", None)
        from_verkey = unpacked.get("sender_verkey", None)
        return message, from_verkey, to_verkey
