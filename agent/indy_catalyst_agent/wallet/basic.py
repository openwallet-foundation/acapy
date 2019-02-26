"""In-memory implementation of BaseWallet interface."""

from typing import Sequence

from .base import BaseWallet, KeyInfo, DIDInfo, PairwiseInfo
from .crypto import (
    create_keypair,
    random_seed,
    validate_seed,
    sign_message,
    verify_signed_message,
    anon_crypt_message,
    anon_decrypt_message,
    auth_crypt_message,
    auth_decrypt_message,
    encode_pack_message,
    decode_pack_message,
)
from .error import WalletError, WalletDuplicateError, WalletNotFoundError
from .util import b58_to_bytes, bytes_to_b58


class BasicWallet(BaseWallet):
    """In-memory wallet implementation."""

    def __init__(self, config: dict = None):
        """
        Initialize a `BasicWallet` instance.

        Args:
            config: {name, key, seed, did, auto-create, auto-remove}

        """
        if not config:
            config = {}
        super(BasicWallet, self).__init__(config)
        self._name = config.get("name")
        self._keys = {}
        self._local_dids = {}
        self._pair_dids = {}

    @property
    def opened(self) -> bool:
        """
        Check whether wallet is currently open.

        Returns:
            True

        """
        return True

    async def open(self):
        """Not applicable to in-memory wallet."""
        pass

    async def close(self):
        """Not applicable to in-memory wallet."""
        pass

    async def create_signing_key(
        self, seed: str = None, metadata: dict = None
    ) -> KeyInfo:
        """
        Create a new public/private signing keypair.

        Args:
            seed: Seed to use for signing key
            metadata: Optional metadata to store with the keypair

        Returns:
            A `KeyInfo` representing the new record

        Raises:
            WalletDuplicateError: If the resulting verkey already exists in the wallet

        """
        seed = validate_seed(seed) or random_seed()
        verkey, secret = create_keypair(seed)
        verkey_enc = bytes_to_b58(verkey)
        if verkey_enc in self._keys:
            raise WalletDuplicateError("Verification key already present in wallet")
        self._keys[verkey_enc] = {
            "seed": seed,
            "secret": secret,
            "verkey": verkey_enc,
            "metadata": metadata.copy() if metadata else {},
        }
        return KeyInfo(verkey_enc, self._keys[verkey_enc]["metadata"].copy())

    async def get_signing_key(self, verkey: str) -> KeyInfo:
        """
        Fetch info for a signing keypair.

        Args:
            verkey: The verification key of the keypair

        Returns:
            A `KeyInfo` representing the keypair

        Raises:
            WalletNotFoundError: if no keypair is associated with the verification key

        """
        if verkey not in self._keys:
            raise WalletNotFoundError("Key not found: {}".format(verkey))
        key = self._keys[verkey]
        return KeyInfo(key["verkey"], key["metadata"].copy())

    async def replace_signing_key_metadata(self, verkey: str, metadata: dict):
        """
        Replace the metadata associated with a signing keypair.

        Args:
            verkey: The verification key of the keypair
            metadata: The new metadata to store

        Raises:
            WalletNotFoundError: if no keypair is associated with the verification key

        """
        if verkey not in self._keys:
            raise WalletNotFoundError("Key not found: {}".format(verkey))
        self._keys[verkey]["metadata"] = metadata.copy() if metadata else {}

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
            A `DIDInfo` instance representing the created DID

        Raises:
            WalletDuplicateError: If the DID already exists in the wallet

        """
        seed = validate_seed(seed) or random_seed()
        verkey, secret = create_keypair(seed)
        if not did:
            did = bytes_to_b58(verkey[:16])
        if did in self._local_dids:
            raise WalletDuplicateError("DID already exists in wallet")
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
        Convert internal DID record to DIDInfo.

        Args:
            did: The DID to get info for

        Returns:
            A `DIDInfo` instance for the DID

        """
        info = self._local_dids[did]
        return DIDInfo(did=did, verkey=info["verkey"], metadata=info["metadata"].copy())

    async def get_local_dids(self) -> Sequence[DIDInfo]:
        """
        Get list of defined local DIDs.

        Returns:
            A list of locally stored DIDs as `DIDInfo` instances

        """
        ret = [self._get_did_info(did) for did in self._local_dids]
        return ret

    async def get_local_did(self, did: str) -> DIDInfo:
        """
        Find info for a local DID.

        Args:
            did: The DID to get info for

        Returns:
            A `DIDInfo` instance representing the found DID

        Raises:
            WalletNotFoundError: If the DID is not found

        """
        if did not in self._local_dids:
            raise WalletNotFoundError("DID not found: {}".format(did))
        return self._get_did_info(did)

    async def get_local_did_for_verkey(self, verkey: str) -> DIDInfo:
        """
        Resolve a local DID from a verkey.

        Args:
            verkey: The verkey to get the local DID for

        Returns:
            A `DIDInfo` instance representing the found DID

        Raises:
            WalletNotFoundError: If the verkey is not found

        """
        for did, info in self._local_dids.items():
            if info["verkey"] == verkey:
                return self._get_did_info(did)
        raise WalletNotFoundError("Verkey not found: {}".format(verkey))

    async def replace_local_did_metadata(self, did: str, metadata: dict):
        """
        Replace metadata for a local DID.

        Args:
            did: The DID to replace metadata for
            metadata: The new metadata

        Raises:
            WalletNotFoundError: If the DID doesn't exist

        """
        if did not in self._local_dids:
            raise WalletNotFoundError("Unknown DID: {}".format(did))
        self._local_dids[did]["metadata"] = metadata.copy() if metadata else {}

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
            their_did: The other party's DID
            their_verkey: The other party's verkey
            my_did: My DID
            metadata: Metadata to store with this relationship

        Returns:
            A `PairwiseInfo` object representing the pairwise connection

        Raises:
            WalletDuplicateError: If the DID already exists in the wallet

        """
        if my_did:
            my_info = await self.get_local_did(my_did)
        else:
            my_info = await self.create_local_did(
                None, None, {"pairwise_for": their_did}
            )

        if their_did in self._pair_dids:
            raise WalletDuplicateError(
                "Pairwise DID already present in wallet: {}".format(their_did)
            )

        self._pair_dids[their_did] = {
            "my_did": my_info.did,
            "their_verkey": their_verkey,
            "metadata": metadata.copy() if metadata else {},
        }
        return self._get_pairwise_info(their_did)

    def _get_pairwise_info(self, their_did: str) -> PairwiseInfo:
        """
        Convert internal pairwise DID record to `PairwiseInfo`.

        Args:
            their_did: The DID to get `PairwiseInfo` for

        Returns:
            A `PairwiseInfo` instance

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
        Get list of defined pairwise DIDs.

        Returns:
            A list of `PairwiseInfo` instances for all pairwise relationships

        """
        ret = [self._get_pairwise_info(their_did) for their_did in self._pair_dids]
        return ret

    async def get_pairwise_for_did(self, their_did: str) -> PairwiseInfo:
        """
        Find info for a pairwise DID.

        Args:
            their_did: The DID to get a pairwise relationship for

        Returns:
            A `PairwiseInfo` instance representing the relationship

        Raises:
            WalletNotFoundError: If the DID is unknown

        """
        if their_did not in self._pair_dids:
            raise WalletNotFoundError("Unknown target DID: {}".format(their_did))
        return self._get_pairwise_info(their_did)

    async def get_pairwise_for_verkey(self, their_verkey: str) -> PairwiseInfo:
        """
        Resolve a pairwise DID from a verkey.

        Args:
            their_verkey: The verkey to get a pairwise relationship for

        Returns:
            A `PairwiseInfo` instance for the relationship

        Raises:
            WalletNotFoundError: If the verkey is not found

        """
        for did, info in self._pair_dids.items():
            if info["their_verkey"] == their_verkey:
                return self._get_pairwise_info(did)
        raise WalletNotFoundError("Verkey not found: {}".format(their_verkey))

    async def replace_pairwise_metadata(self, their_did: str, metadata: dict):
        """
        Replace metadata for a pairwise DID.

        Args:
            their_did: The DID to replace metadata for
            metadata: The new metadata

        Raises:
            WalletNotFoundError: If the DID is unknown

        """
        if their_did not in self._pair_dids:
            raise WalletNotFoundError("Unknown target DID: {}".format(their_did))
        self._pair_dids[their_did]["metadata"] = metadata.copy() if metadata else {}

    def _get_private_key(self, verkey: str, long=False) -> bytes:
        """
        Resolve private key for a wallet DID.

        Args:
            verkey: The verkey to lookup
            long:

        Returns:
            The private key


        Raises:
            WalletError: If the private key is not found

        """

        keys_and_dids = list(self._local_dids.values()) + list(self._keys.values())
        for info in keys_and_dids:
            if info["verkey"] == verkey:
                return info["secret"] if long else info["seed"]

        raise WalletError("Private key not found for verkey: {}".format(verkey))

    async def sign_message(self, message: bytes, from_verkey: str) -> bytes:
        """
        Sign a message using the private key associated with a given verkey.

        Args:
            message: Message bytes to sign
            from_verkey: The verkey to use to sign

        Returns:
            A signature

        Raises:
            WalletError: If the message is not provided
            WalletError: If the verkey is not provided

        """
        if not message:
            raise WalletError("Message not provided")
        if not from_verkey:
            raise WalletError("Verkey not provided")
        secret = self._get_private_key(from_verkey, True)
        signature = sign_message(message, secret)
        return signature

    async def verify_message(
        self, message: bytes, signature: bytes, from_verkey: str
    ) -> bool:
        """
        Verify a signature against the public key of the signer.

        Args:
            message: Message to verify
            signature: Signature to verify
            from_verkey: Verkey to use in verification

        Returns:
            True if verified, else False

        Raises:
            WalletError: If the verkey is not provided
            WalletError: If the signature is not provided
            WalletError: If the message is not provided

        """
        if not from_verkey:
            raise WalletError("Verkey not provided")
        if not signature:
            raise WalletError("Signature not provided")
        if not message:
            raise WalletError("Message not provided")
        verkey_bytes = b58_to_bytes(from_verkey)
        verified = verify_signed_message(signature + message, verkey_bytes)
        return verified

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
        to_verkey_bytes = b58_to_bytes(to_verkey)
        if from_verkey:
            secret = self._get_private_key(from_verkey)
            result = auth_crypt_message(message, to_verkey_bytes, secret)
        else:
            result = anon_crypt_message(message, to_verkey_bytes)
        return result

    async def decrypt_message(
        self, enc_message: bytes, to_verkey: str, use_auth: bool
    ) -> (bytes, str):
        """
        Decrypt a message assembled by auth_crypt or anon_crypt.

        Args:
            message: The encrypted message content
            to_verkey: The verkey of the recipient. If provided then auth_decrypt is
                used, otherwise anon_decrypt is used.
            use_auth: True if you would like to auth_decrypt, False for anon_decrypt

        Returns:
            A tuple of the decrypted message content and sender verkey
            (None for anon_crypt)

        """
        secret = self._get_private_key(to_verkey)
        if use_auth:
            message, from_verkey = auth_decrypt_message(enc_message, secret)
        else:
            message = anon_decrypt_message(enc_message, secret)
            from_verkey = None
        return message, from_verkey

    async def pack_message(
        self, message: str, to_verkeys: Sequence[str], from_verkey: str = None
    ) -> bytes:
        """
        Pack a message for one or more recipients.

        Args:
            message: The message to pack
            to_verkeys: List of verkeys to pack for
            from_verkey: Sender verkey to pack from

        Returns:
            The resulting packed message bytes

        """
        keys_bin = [b58_to_bytes(key) for key in to_verkeys]
        secret = self._get_private_key(from_verkey) if from_verkey else None
        result = encode_pack_message(message, keys_bin, secret)
        return result

    async def unpack_message(self, enc_message: bytes) -> (str, str, str):
        """
        Unpack a message.

        Args:
            enc_message: The packed message bytes

        Returns:
            A tuple: (message, from_verkey, to_verkey)

        Raises:
            WalletError: If the message is not provided
            WalletError: If there is a problem unpacking the message

        """
        if not enc_message:
            raise WalletError("Message not provided")
        try:
            message, from_verkey, to_verkey = decode_pack_message(
                enc_message, lambda k: self._get_private_key(k, True)
            )
        except ValueError as e:
            raise WalletError("Message could not be unpacked: {}".format(str(e)))
        return message, from_verkey, to_verkey
