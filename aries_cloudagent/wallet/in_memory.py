"""In-memory implementation of BaseWallet interface."""

import asyncio
from typing import List, Sequence, Tuple, Union

from .did_parameters_validation import DIDParametersValidation
from ..core.in_memory import InMemoryProfile

from .base import BaseWallet
from .crypto import (
    create_keypair,
    validate_seed,
    sign_message,
    verify_signed_message,
    encode_pack_message,
    decode_pack_message,
)
from .did_info import KeyInfo, DIDInfo
from .did_posture import DIDPosture
from .did_method import DIDMethod, DIDMethods
from .error import WalletError, WalletDuplicateError, WalletNotFoundError
from .key_type import KeyType
from .util import b58_to_bytes, bytes_to_b58, random_seed


class InMemoryWallet(BaseWallet):
    """In-memory wallet implementation."""

    def __init__(self, profile: InMemoryProfile):
        """
        Initialize an `InMemoryWallet` instance.

        Args:
            profile: The in-memory profile used to store state

        """
        self.profile = profile

    async def create_signing_key(
        self,
        key_type: KeyType,
        seed: str = None,
        metadata: dict = None,
    ) -> KeyInfo:
        """
        Create a new public/private signing keypair.

        Args:
            seed: Seed to use for signing key
            metadata: Optional metadata to store with the keypair
            key_type: Key type to generate. Default to ed25519

        Returns:
            A `KeyInfo` representing the new record

        Raises:
            WalletDuplicateError: If the resulting verkey already exists in the wallet

        """
        seed = validate_seed(seed) or random_seed()
        verkey, secret = create_keypair(key_type, seed)
        verkey_enc = bytes_to_b58(verkey)
        if verkey_enc in self.profile.keys:
            raise WalletDuplicateError("Verification key already present in wallet")
        self.profile.keys[verkey_enc] = {
            "seed": seed,
            "secret": secret,
            "verkey": verkey_enc,
            "metadata": metadata.copy() if metadata else {},
            "key_type": key_type,
        }
        return KeyInfo(
            verkey=verkey_enc,
            metadata=self.profile.keys[verkey_enc]["metadata"].copy(),
            key_type=key_type,
        )

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
        if verkey not in self.profile.keys:
            raise WalletNotFoundError("Key not found: {}".format(verkey))
        key = self.profile.keys[verkey]
        return KeyInfo(
            verkey=key["verkey"],
            metadata=key["metadata"].copy(),
            key_type=key["key_type"],
        )

    async def replace_signing_key_metadata(self, verkey: str, metadata: dict):
        """
        Replace the metadata associated with a signing keypair.

        Args:
            verkey: The verification key of the keypair
            metadata: The new metadata to store

        Raises:
            WalletNotFoundError: if no keypair is associated with the verification key

        """
        if verkey not in self.profile.keys:
            raise WalletNotFoundError("Key not found: {}".format(verkey))
        self.profile.keys[verkey]["metadata"] = metadata.copy() if metadata else {}

    async def rotate_did_keypair_start(self, did: str, next_seed: str = None) -> str:
        """
        Begin key rotation for DID that wallet owns: generate new keypair.

        Args:
            did: signing DID
            next_seed: incoming replacement seed (default random)

        Returns:
            The new verification key

        Raises:
            WalletNotFoundError: if wallet does not own DID

        """
        local_did = self.profile.local_dids.get(did)
        if not local_did:
            raise WalletNotFoundError("Wallet owns no such DID: {}".format(did))
        did_methods: DIDMethods = self.profile.context.inject(DIDMethods)
        did_method: DIDMethod = did_methods.from_did(did)
        if not did_method.supports_rotation:
            raise WalletError(
                f"DID method '{did_method.method_name}' does not support key rotation."
            )

        key_info = await self.create_signing_key(
            key_type=local_did["key_type"], seed=next_seed, metadata={"did": did}
        )
        return key_info.verkey

    async def rotate_did_keypair_apply(self, did: str) -> None:
        """
        Apply temporary keypair as main for DID that wallet owns.

        Args:
            did: signing DID

        Raises:
            WalletNotFoundError: if wallet does not own DID
            WalletError: if wallet has not started key rotation

        """
        if did not in self.profile.local_dids:
            raise WalletNotFoundError("Wallet owns no such DID: {}".format(did))
        temp_keys = [
            k
            for k in self.profile.keys
            if self.profile.keys[k]["metadata"].get("did") == did
        ]
        if not temp_keys:
            raise WalletError("Key rotation not in progress for DID: {}".format(did))
        verkey_enc = temp_keys[0]

        local_did = self.profile.local_dids[did]

        local_did.update(
            {
                "seed": self.profile.keys[verkey_enc]["seed"],
                "secret": self.profile.keys[verkey_enc]["secret"],
                "verkey": verkey_enc,
            }
        )
        self.profile.keys.pop(verkey_enc)
        return DIDInfo(
            did=did,
            verkey=verkey_enc,
            metadata=local_did["metadata"].copy(),
            method=local_did["method"],
            key_type=local_did["key_type"],
        )

    async def create_local_did(
        self,
        method: DIDMethod,
        key_type: KeyType,
        seed: str = None,
        did: str = None,
        metadata: dict = None,
    ) -> DIDInfo:
        """
        Create and store a new local DID.

        Args:
            method: The method to use for the DID
            key_type: The key type to use for the DID
            seed: Optional seed to use for DID
            did: The DID to use
            metadata: Metadata to store with DID

        Returns:
            A `DIDInfo` instance representing the created DID

        Raises:
            WalletDuplicateError: If the DID already exists in the wallet

        """
        seed = validate_seed(seed) or random_seed()

        did_methods: DIDMethods = self.profile.context.inject(DIDMethods)
        did_validation = DIDParametersValidation(did_methods)

        did_validation.validate_key_type(method, key_type)

        verkey, secret = create_keypair(key_type, seed)
        verkey_enc = bytes_to_b58(verkey)

        did = did_validation.validate_or_derive_did(method, key_type, verkey, did)

        if (
            did in self.profile.local_dids
            and self.profile.local_dids[did]["verkey"] != verkey_enc
        ):
            raise WalletDuplicateError("DID already exists in wallet")
        self.profile.local_dids[did] = {
            "seed": seed,
            "secret": secret,
            "verkey": verkey_enc,
            "metadata": metadata.copy() if metadata else {},
            "key_type": key_type,
            "method": method,
        }
        return DIDInfo(
            did=did,
            verkey=verkey_enc,
            metadata=self.profile.local_dids[did]["metadata"].copy(),
            method=method,
            key_type=key_type,
        )

    def _get_did_info(self, did: str) -> DIDInfo:
        """
        Convert internal DID record to DIDInfo.

        Args:
            did: The DID to get info for

        Returns:
            A `DIDInfo` instance for the DID

        """
        info = self.profile.local_dids[did]
        return DIDInfo(
            did=did,
            verkey=info["verkey"],
            metadata=info["metadata"].copy(),
            method=info["method"],
            key_type=info["key_type"],
        )

    async def get_local_dids(self) -> Sequence[DIDInfo]:
        """
        Get list of defined local DIDs.

        Returns:
            A list of locally stored DIDs as `DIDInfo` instances

        """
        ret = [self._get_did_info(did) for did in self.profile.local_dids]
        return ret

    async def get_local_did(self, did: str) -> DIDInfo:
        """
        Find info for a local DID.

        Args:
            did: The DID for which to get info

        Returns:
            A `DIDInfo` instance representing the found DID

        Raises:
            WalletNotFoundError: If the DID is not found

        """
        if did not in self.profile.local_dids:
            raise WalletNotFoundError("DID not found: {}".format(did))
        return self._get_did_info(did)

    async def get_local_did_for_verkey(self, verkey: str) -> DIDInfo:
        """
        Resolve a local DID from a verkey.

        Args:
            verkey: The verkey for which to get the local DID

        Returns:
            A `DIDInfo` instance representing the found DID

        Raises:
            WalletNotFoundError: If the verkey is not found

        """
        for did, info in self.profile.local_dids.items():
            if info["verkey"] == verkey:
                return self._get_did_info(did)
        raise WalletNotFoundError("Verkey not found: {}".format(verkey))

    async def replace_local_did_metadata(self, did: str, metadata: dict):
        """
        Replace metadata for a local DID.

        Args:
            did: The DID for which to replace metadata
            metadata: The new metadata

        Raises:
            WalletNotFoundError: If the DID doesn't exist

        """
        if did not in self.profile.local_dids:
            raise WalletNotFoundError("Unknown DID: {}".format(did))
        self.profile.local_dids[did]["metadata"] = metadata.copy() if metadata else {}

    def _get_private_key(self, verkey: str) -> bytes:
        """
        Resolve private key for a wallet DID.

        Args:
            verkey: The verkey to lookup

        Returns:
            The private key

        Raises:
            WalletError: If the private key is not found

        """

        keys_and_dids = list(self.profile.local_dids.values()) + list(
            self.profile.keys.values()
        )
        for info in keys_and_dids:
            if info["verkey"] == verkey:
                return info["secret"]

        raise WalletError("Private key not found for verkey: {}".format(verkey))

    async def get_public_did(self) -> DIDInfo:
        """
        Retrieve the public DID.

        Returns:
            The currently public `DIDInfo`, if any

        """

        dids = await self.get_local_dids()
        for info in dids:
            if info.metadata.get("public"):
                return info

        return None

    async def set_public_did(self, did: Union[str, DIDInfo]) -> DIDInfo:
        """
        Assign the public DID.

        Returns:
            The updated `DIDInfo`

        """

        if isinstance(did, str):
            # will raise an exception if not found
            info = await self.get_local_did(did)
        else:
            info = did
            did = info.did

        public = await self.get_public_did()
        if public and public.did == did:
            info = public
        else:
            if public:
                metadata = {**public.metadata, **DIDPosture.POSTED.metadata}
                await self.replace_local_did_metadata(public.did, metadata)

            metadata = {**info.metadata, **DIDPosture.PUBLIC.metadata}
            await self.replace_local_did_metadata(did, metadata)
            info = await self.get_local_did(did)

        return info

    async def sign_message(
        self, message: Union[List[bytes], bytes], from_verkey: str
    ) -> bytes:
        """
        Sign message(s) using the private key associated with a given verkey.

        Args:
            message: Message(s) bytes to sign
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

        try:
            key_info = await self.get_signing_key(from_verkey)
        except WalletNotFoundError:
            key_info = await self.get_local_did_for_verkey(from_verkey)

        secret = self._get_private_key(from_verkey)
        signature = sign_message(message, secret, key_info.key_type)
        return signature

    async def verify_message(
        self,
        message: Union[List[bytes], bytes],
        signature: bytes,
        from_verkey: str,
        key_type: KeyType,
    ) -> bool:
        """
        Verify a signature against the public key of the signer.

        Args:
            message: Message(s) to verify
            signature: Signature to verify
            from_verkey: Verkey to use in verification
            key_type: The key type to derive the signature verification algorithm from

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

        verified = verify_signed_message(message, signature, verkey_bytes, key_type)
        return verified

    async def pack_message(
        self, message: str, to_verkeys: Sequence[str], from_verkey: str = None
    ) -> bytes:
        """
        Pack a message for one or more recipients.

        Args:
            message: The message to pack
            to_verkeys: List of verkeys for which to pack
            from_verkey: Sender verkey from which to pack

        Returns:
            The resulting packed message bytes

        Raises:
            WalletError: If the message is not provided

        """
        if message is None:
            raise WalletError("Message not provided")

        keys_bin = [b58_to_bytes(key) for key in to_verkeys]
        secret = self._get_private_key(from_verkey) if from_verkey else None
        result = await asyncio.get_event_loop().run_in_executor(
            None, encode_pack_message, message, keys_bin, secret
        )
        return result

    async def unpack_message(self, enc_message: bytes) -> Tuple[str, str, str]:
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
            (
                message,
                from_verkey,
                to_verkey,
            ) = await asyncio.get_event_loop().run_in_executor(
                None, lambda: decode_pack_message(enc_message, self._get_private_key)
            )
        except ValueError as e:
            raise WalletError("Message could not be unpacked: {}".format(str(e)))
        return message, from_verkey, to_verkey
