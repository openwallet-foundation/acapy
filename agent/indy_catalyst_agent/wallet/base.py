"""
Wallet base class
"""

from abc import ABC, abstractmethod
from collections import namedtuple
from typing import Sequence


DIDInfo = namedtuple("DIDInfo", "did verkey metadata tempVerkey")


class BaseWallet(ABC):
    """
    Abstract wallet interface
    """

    def __init__(self, config: dict):
        """
        config: {name, key, seed, did, auto-create, auto-remove}
        """
        pass

    @property
    def handle(self):
        """
        Get internal wallet reference
        """
        return None

    @property
    def opened(self) -> bool:
        """
        Check whether wallet is currently open
        """
        return False

    @abstractmethod
    async def open(self):
        """
        Open wallet, removing and/or creating it if so configured
        """
        pass

    @abstractmethod
    async def close(self):
        """
        Close previously-opened wallet, removing it if so configured
        """
        pass

    @abstractmethod
    async def get_local_dids(self) -> Sequence[DIDInfo]:
        """
        Get list of defined local DIDs
        """
        pass

    @abstractmethod
    async def create_local_did(self, seed: str = None, did: str = None, metadata: dict = None) -> str:
        """
        Create and store a new local DID
        """
        pass

    @abstractmethod
    async def get_local_did_for_verkey(self, verkey: str) -> str:
        """
        Resolve a local DID from a verkey
        """
        pass

    @abstractmethod
    async def get_local_verkey_for_did(self, did: str) -> str:
        """
        Resolve a local verkey from a DID
        """
        pass

    @abstractmethod
    async def get_local_did_metadata(self, did: str) -> dict:
        """
        Get metadata for a local DID
        """
        pass

    @abstractmethod
    async def replace_local_did_metadata(self, did: str, metadata: dict):
        """
        Replace metadata for a local DID
        """
        pass

    @abstractmethod
    async def create_pairwise_did(self, to_did: str, from_did: str, metadata: dict = None) -> str:
        """
        Create a new pairwise DID for a secure connection
        """
        pass

    @abstractmethod
    async def get_pairwise_did_for_verkey(self, verkey: str) -> str:
        """
        Resolve a pairwise DID from a verkey
        """
        pass

    @abstractmethod
    async def get_pairwise_did_metadata(self, did: str) -> dict:
        """
        Get metadata for a pairwise DID
        """
        pass

    @abstractmethod
    async def replace_pairwise_did_metadata(self, did: str, metadata: dict):
        """
        Replace metadata for a pairwise DID
        """
        pass

    @abstractmethod
    async def sign_message(self, message: bytes, from_verkey: str) -> bytes:
        """
        Sign a message using the private key associated with a given verkey
        """
        pass

    @abstractmethod
    async def verify_message(self, message: bytes, signature: bytes, from_verkey: str) -> bool:
        """
        Verify a signature against the public key of the signer
        """
        pass

    @abstractmethod
    async def pack_message(self, message: str, to_verkeys: Sequence[str], from_verkey: str = None) -> bytes:
        """
        Pack a message for one or more recipients
        """
        pass

    @abstractmethod
    async def unpack_message(self, message_json: bytes) -> (str, str, str):
        """
        Unpack a message
        """
        pass


    # TODO:
    # store credential (return ID)
    # fetch credentials by ID, [or query, filter, proof request?]
