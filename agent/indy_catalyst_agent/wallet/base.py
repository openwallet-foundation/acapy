"""
Wallet base class
"""

from abc import ABC, abstractmethod
from collections import namedtuple
from typing import Sequence

KeyInfo = namedtuple("KeyInfo", "verkey metadata")

DIDInfo = namedtuple("DIDInfo", "did verkey metadata")

PairwiseInfo = namedtuple(
    "PairwiseInfo", "their_did their_verkey my_did my_verkey metadata"
)


class BaseWallet(ABC):
    """Abstract wallet interface"""

    def __init__(self, config: dict):
        """
        config: {name, key, seed, did, auto-create, auto-remove}
        """

    @property
    def handle(self):
        """Get internal wallet reference"""
        return None

    @property
    def opened(self) -> bool:
        """Check whether wallet is currently open"""
        return False

    @abstractmethod
    async def open(self):
        """
        Open wallet, removing and/or creating it if so configured
        """

    @abstractmethod
    async def close(self):
        """
        Close previously-opened wallet, removing it if so configured
        """

    @abstractmethod
    async def create_signing_key(
        self, seed: str = None, metadata: dict = None
    ) -> KeyInfo:
        """
        Create a new public/private signing keypair

        Args:
            seed: Optional seed allowing deterministic key creation
            metadata: Optional metadata to store with the keypair

        Returns: a `KeyInfo` representing the new record

        Raises:
            WalletDuplicateError: If the resulting verkey already exists in the wallet
        """

    @abstractmethod
    async def get_signing_key(self, verkey: str) -> KeyInfo:
        """
        Fetch info for a signing keypair

        Args:
            verkey: The verification key of the keypair

        Returns: a `KeyInfo` representing the keypair

        Raises:
            WalletNotFoundError: if no keypair is associated with the verification key
        """

    @abstractmethod
    async def replace_signing_key_metadata(self, verkey: str, metadata: dict):
        """
        Replace the metadata associated with a signing keypair

        Args:
            verkey: The verification key of the keypair
            metadata: The new metadata to store

        Raises:
            WalletNotFoundError: if no keypair is associated with the verification key
        """

    @abstractmethod
    async def create_local_did(
        self, seed: str = None, did: str = None, metadata: dict = None
    ) -> DIDInfo:
        """
        Create and store a new local DID
        """

    @abstractmethod
    async def get_local_dids(self) -> Sequence[DIDInfo]:
        """
        Get list of defined local DIDs
        """

    @abstractmethod
    async def get_local_did(self, did: str) -> DIDInfo:
        """
        Find info for a local DID
        """

    @abstractmethod
    async def get_local_did_for_verkey(self, verkey: str) -> DIDInfo:
        """
        Resolve a local DID from a verkey
        """

    @abstractmethod
    async def replace_local_did_metadata(self, did: str, metadata: dict):
        """
        Replace the metadata associated with a local DID
        """

    @abstractmethod
    async def create_pairwise(
        self,
        their_did: str,
        their_verkey: str,
        my_did: str = None,
        metadata: dict = None,
    ) -> PairwiseInfo:
        """
        Create a new pairwise DID for a secure connection
        """

    @abstractmethod
    async def get_pairwise_list(self) -> Sequence[PairwiseInfo]:
        """
        Get list of defined pairwise DIDs
        """

    @abstractmethod
    async def get_pairwise_for_did(self, their_did: str) -> PairwiseInfo:
        """
        Find info for a pairwise DID
        """

    @abstractmethod
    async def get_pairwise_for_verkey(self, their_verkey: str) -> PairwiseInfo:
        """
        Resolve a pairwise DID from a verkey
        """

    @abstractmethod
    async def replace_pairwise_metadata(self, their_did: str, metadata: dict):
        """
        Replace the metadata associated with a pairwise DID
        """

    @abstractmethod
    async def sign_message(self, message: bytes, from_verkey: str) -> bytes:
        """
        Sign a message using the private key associated with a given verkey
        """

    @abstractmethod
    async def verify_message(
        self, message: bytes, signature: bytes, from_verkey: str
    ) -> bool:
        """
        Verify a signature against the public key of the signer
        """

    @abstractmethod
    async def encrypt_message(
        self, message: bytes, to_verkey: str, from_verkey: str = None
    ) -> bytes:
        """
        Apply auth_crypt or anon_crypt to a message

        Args:
            message: The binary message content
            to_verkey: The verkey of the recipient
            from_verkey: The verkey of the sender. If provided then auth_crypt is used,
                otherwise anon_crypt is used.

        Returns:
            The encrypted message content
        """

    @abstractmethod
    async def decrypt_message(
        self, enc_message: bytes, to_verkey: str, use_auth: bool
    ) -> (bytes, str):
        """
        Decrypt a message assembled by auth_crypt or anon_crypt

        Args:
            message: The encrypted message content
            to_verkey: The verkey of the recipient. If provided then auth_decrypt is
                used, otherwise anon_decrypt is used.

        Returns:
            A tuple of the decrypted message content and sender verkey
            (None for anon_crypt)
        """

    @abstractmethod
    async def pack_message(
        self, message: str, to_verkeys: Sequence[str], from_verkey: str = None
    ) -> bytes:
        """
        Pack a message for one or more recipients
        """

    @abstractmethod
    async def unpack_message(self, enc_message: bytes) -> (str, str, str):
        """
        Unpack a message
        """

    # TODO:
    # store credential (return ID)
    # fetch credentials by ID [or query, filter, proof request?]

    def __repr__(self) -> str:
        return "<{}(opened={})>".format(self.__class__.__name__, self.opened)
