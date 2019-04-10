"""Wallet base class."""

from abc import ABC, abstractmethod
from collections import namedtuple
from typing import Sequence

KeyInfo = namedtuple("KeyInfo", "verkey metadata")

DIDInfo = namedtuple("DIDInfo", "did verkey metadata")

PairwiseInfo = namedtuple(
    "PairwiseInfo", "their_did their_verkey my_did my_verkey metadata"
)


class BaseWallet(ABC):
    """Abstract wallet interface."""

    # TODO: break config out into params?
    def __init__(self, config: dict):
        """
        Initialize a `BaseWallet` instance.

        Args:
            config: {name, key, seed, did, auto-create, auto-remove}

        """

    @property
    def handle(self):
        """
        Get internal wallet reference.

        Returns:
            Defaults to None

        """
        return None

    @property
    def opened(self) -> bool:
        """
        Check whether wallet is currently open.

        Returns:
            Defaults to False

        """
        return False

    @abstractmethod
    async def open(self):
        """Open wallet, removing and/or creating it if so configured."""

    @abstractmethod
    async def close(self):
        """Close previously-opened wallet, removing it if so configured."""

    @abstractmethod
    async def create_signing_key(
        self, seed: str = None, metadata: dict = None
    ) -> KeyInfo:
        """
        Create a new public/private signing keypair.

        Args:
            seed: Optional seed allowing deterministic key creation
            metadata: Optional metadata to store with the keypair

        Returns:
            A `KeyInfo` representing the new record

        """

    @abstractmethod
    async def get_signing_key(self, verkey: str) -> KeyInfo:
        """
        Fetch info for a signing keypair.

        Args:
            verkey: The verification key of the keypair

        Returns:
            A `KeyInfo` representing the keypair

        """

    @abstractmethod
    async def replace_signing_key_metadata(self, verkey: str, metadata: dict):
        """
        Replace the metadata associated with a signing keypair.

        Args:
            verkey: The verification key of the keypair
            metadata: The new metadata to store

        """

    @abstractmethod
    async def create_local_did(
        self, seed: str = None, did: str = None, metadata: dict = None
    ) -> DIDInfo:
        """
        Create and store a new local DID.

        Args:
            seed: Optional seed to use for did
            did: The DID to use
            metadata: Metadata to store with DID

        Returns:
            The created `DIDInfo`

        """

    async def create_public_did(
        self, seed: str = None, did: str = None, metadata: dict = {}
    ) -> DIDInfo:
        """
        Create and store a new public DID.

        Implicitly flags all other dids as not public.

        Args:
            seed: Optional seed to use for did
            did: The DID to use
            metadata: Metadata to store with DID

        Returns:
            The created `DIDInfo`

        """

        metadata["public"] = True
        dids = await self.get_local_dids()
        for info in dids:
            info_meta = info.metadata
            info_meta["public"] = False
            await self.replace_local_did_metadata(info.did, info_meta)
        return await self.create_local_did(seed, did, metadata)

    async def get_public_did(self) -> DIDInfo:
        """
        Retrieve the public did.

        Returns:
            The created `DIDInfo`

        """

        dids = await self.get_local_dids()
        for info in dids:
            if "public" in info.metadata and info.metadata["public"] is True:
                return info

        return None

    @abstractmethod
    async def get_local_dids(self) -> Sequence[DIDInfo]:
        """
        Get list of defined local DIDs.

        Returns:
            A list of `DIDInfo` instances

        """

    @abstractmethod
    async def get_local_did(self, did: str) -> DIDInfo:
        """
        Find info for a local DID.

        Args:
            did: The DID to get info for

        Returns:
            A `DIDInfo` instance for the DID

        """

    @abstractmethod
    async def get_local_did_for_verkey(self, verkey: str) -> DIDInfo:
        """
        Resolve a local DID from a verkey.

        Args:
            verkey: Verkey to get DID info for

        Returns:
            A `DIDInfo` instance for the DID

        """

    @abstractmethod
    async def replace_local_did_metadata(self, did: str, metadata: dict):
        """
        Replace the metadata associated with a local DID.

        Args:
            did: DID to replace metadata for
            metadata: The new metadata

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
        Create a new pairwise DID for a secure connection.

        Args:
            their_did: Their DID
            their_verkey: Their verkey
            my_did: My DID
            metadata: Metadata for relationship

        Returns:
            A `PairwiseInfo` instance representing the new relationship

        """

    @abstractmethod
    async def get_pairwise_list(self) -> Sequence[PairwiseInfo]:
        """
        Get list of defined pairwise DIDs.

        Returns:
            A list of `PairwiseInfo` instances for all relationships

        """

    @abstractmethod
    async def get_pairwise_for_did(self, their_did: str) -> PairwiseInfo:
        """
        Find info for a pairwise DID.

        Args:
            their_did: The DID representing the relationship

        Returns:
            A `PairwiseInfo` instance representing the relationship

        """

    @abstractmethod
    async def get_pairwise_for_verkey(self, their_verkey: str) -> PairwiseInfo:
        """
        Resolve a pairwise DID from a verkey.

        Args:
            their_verkey: The verkey representing the relationship

        Returns:
            A `PairwiseInfo` instance representing the relationship

        """

    @abstractmethod
    async def replace_pairwise_metadata(self, their_did: str, metadata: dict):
        """
        Replace the metadata associated with a pairwise DID.

        Args:
            their_did: The did representing the relationship
            metadata: The new metadata

        """

    @abstractmethod
    async def sign_message(self, message: bytes, from_verkey: str) -> bytes:
        """
        Sign a message using the private key associated with a given verkey.

        Args:
            message: The message to sign
            from_verkey: Sign using the private key related to this verkey

        Returns:
            The signature

        """

    @abstractmethod
    async def verify_message(
        self, message: bytes, signature: bytes, from_verkey: str
    ) -> bool:
        """
        Verify a signature against the public key of the signer.

        Args:
            message: The message to verify
            signature: The signature to verify
            from_verkey: Verkey to use in verification

        Returns:
            True if verified, else False

        """

    @abstractmethod
    async def encrypt_message(
        self, message: bytes, to_verkey: str, from_verkey: str = None
    ) -> bytes:
        """
        Apply auth_crypt or anon_crypt to a message.

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
        Decrypt a message assembled by auth_crypt or anon_crypt.

        Args:
            enc_message: The encrypted message content
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
        Pack a message for one or more recipients.

        Args:
            message: The message to pack
            to_verkeys: The verkeys to pack the message for
            from_verkey: The sender verkey

        Returns:
            The packed message

        """

    @abstractmethod
    async def unpack_message(self, enc_message: bytes) -> (str, str, str):
        """
        Unpack a message.

        Args:
            enc_message: The encrypted message

        Returns:
            A tuple: (message, from_verkey, to_verkey)

        """

    # TODO:
    # store credential (return ID)
    # fetch credentials by ID [or query, filter, proof request?]

    def __repr__(self) -> str:
        """Get a human readable string."""
        return "<{}(opened={})>".format(self.__class__.__name__, self.opened)
