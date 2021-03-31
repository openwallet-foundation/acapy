"""Cryptography functions used by BasicWallet."""

import uuid
from enum import Enum
import json

from collections import OrderedDict
from typing import Callable, Mapping, NamedTuple, Optional, Sequence, Tuple, Union, List

import nacl.bindings
import nacl.exceptions
import nacl.utils

from ..storage.base import BaseStorage
from ..storage.record import StorageRecord
from marshmallow import fields, Schema, ValidationError
from ursa_bbs_signatures.models.SignRequest import SignRequest
from ursa_bbs_signatures.models.VerifyRequest import VerifyRequest
from ursa_bbs_signatures.models.keys.BlsKeyPair import BlsKeyPair
from ursa_bbs_signatures.api import sign as bbs_sign, verify as bbs_verify

from .error import WalletError
from ..core.error import BaseError
from .util import (
    bytes_to_b58,
    bytes_to_b64,
    b64_to_bytes,
    b58_to_bytes,
)

# Define keys
KeySpec = NamedTuple(
    "KeySpec",
    [("key_type", str), ("multicodec_name", str), ("multicodec_prefix", int)],
)


class KeyTypeException(BaseException):
    """Key type exception."""


class KeyType(Enum):
    """KeyType Enum specifying key types with multicodec name."""

    # NOTE: the py_multicodec library is outdated. We use hardcoded prefixes here
    # until this PR gets merged: https://github.com/multiformats/py-multicodec/pull/14
    # multicodec is also not used now, but may be used again if py_multicodec is updated
    ED25519 = KeySpec("ed25519", "ed25519-pub", b"\xed\x01")
    X25519 = KeySpec("x25519", "x25519-pub", b"\xec\x01")
    BLS12381G1 = KeySpec("bls12381g1", "bls12_381-g1-pub", b"\xea\x01")
    BLS12381G2 = KeySpec("bls12381g2", "bls12_381-g2-pub", b"\xeb\x01")
    BLS12381G1G2 = KeySpec("bls12381g1g2", "bls12_381-g1g2-pub", b"\xee\x01")

    @property
    def key_type(self) -> str:
        """Getter for key type identifier."""
        return self.value.key_type

    @property
    def multicodec_name(self) -> str:
        """Getter for multicodec name."""
        return self.value.multicodec_name

    @property
    def multicodec_prefix(self) -> bytes:
        """Getter for multicodec prefix."""
        return self.value.multicodec_prefix

    @classmethod
    def from_multicodec_name(cls, multicodec_name: str) -> Optional["KeyType"]:
        """Get KeyType instance based on multicodec name. Returns None if not found."""
        for key_type in KeyType:
            if key_type.multicodec_name == multicodec_name:
                return key_type

        return None

    @classmethod
    def from_multicodec_prefix(cls, multicodec_prefix: bytes) -> Optional["KeyType"]:
        """Get KeyType instance based on multicodec prefix. Returns None if not found."""
        for key_type in KeyType:
            if key_type.multicodec_prefix == multicodec_prefix:
                return key_type

        return None

    @classmethod
    def from_prefixed_bytes(cls, prefixed_bytes: bytes) -> Optional["KeyType"]:
        """Get KeyType instance based on prefix in bytes. Returns None if not found."""
        for key_type in KeyType:
            if prefixed_bytes.startswith(key_type.multicodec_prefix):
                return key_type

        return None

    @classmethod
    def from_key_type(cls, key_type: str) -> Optional["KeyType"]:
        """Get KeyType instance from the key type identifier."""
        for _key_type in KeyType:
            if _key_type.key_type == key_type:
                return _key_type

        return None


DIDMethodSpec = NamedTuple(
    "DIDMethodSpec",
    [
        ("method_name", str),
        ("supported_key_types", List[KeyType]),
        ("supports_rotation", bool),
    ],
)


class DIDMethod(Enum):
    """DID Method class specifying DID methods with supported key types."""

    SOV = DIDMethodSpec(
        method_name="sov", supported_key_types=[KeyType.ED25519], supports_rotation=True
    )
    KEY = DIDMethodSpec(
        method_name="key",
        supported_key_types=[KeyType.ED25519, KeyType.BLS12381G2],
        supports_rotation=False,
    )

    @property
    def method_name(self) -> str:
        """Getter for did method name. e.g. sov or key."""
        return self.value.method_name

    @property
    def supported_key_types(self) -> List[KeyType]:
        """Getter for supported key types of method."""
        return self.value.supported_key_types

    @property
    def supports_rotation(self) -> bool:
        """Check whether the current method supports key rotation."""
        return self.value.supports_rotation

    def supports_key_type(self, key_type: KeyType) -> bool:
        """Check whether the current method supports the key type."""
        return key_type in self.supported_key_types

    def from_metadata(metadata: Mapping) -> "DIDMethod":
        """Get DID method instance from metadata object.

        Returns SOV if no metadata was found for backwards compatability.
        """
        method = metadata.get("method")

        # extract from metadata object
        if method:
            for did_method in DIDMethod:
                if method == did_method.method_name:
                    return did_method

        # return default SOV for backward compat
        return DIDMethod.SOV

    def from_method(method: str) -> Optional["DIDMethod"]:
        """Get DID method instance from the method name."""
        for did_method in DIDMethod:
            if method == did_method.method_name:
                return did_method

        return None

    def from_did(did: str) -> "DIDMethod":
        """Get DID method instance from the method name."""
        if not did.startswith("did:"):
            # sov has no prefix
            return DIDMethod.SOV

        parts = did.split(":")
        method_str = parts[1]

        method = DIDMethod.from_method(method_str)

        if not method:
            raise BaseError(f"Unsupported did method: {method_str}")

        return method


class PackMessageSchema(Schema):
    """Packed message schema."""

    protected = fields.Str(required=True)
    iv = fields.Str(required=True)
    tag = fields.Str(required=True)
    ciphertext = fields.Str(required=True)


class PackRecipientHeaderSchema(Schema):
    """Packed recipient header schema."""

    kid = fields.Str(required=True)
    sender = fields.Str(required=False, allow_none=True)
    iv = fields.Str(required=False, allow_none=True)


class PackRecipientSchema(Schema):
    """Packed recipient schema."""

    encrypted_key = fields.Str(required=True)
    header = fields.Nested(PackRecipientHeaderSchema(), required=True)


class PackRecipientsSchema(Schema):
    """Packed recipients schema."""

    enc = fields.Constant("xchacha20poly1305_ietf", required=True)
    typ = fields.Constant("JWM/1.0", required=True)
    alg = fields.Str(required=True)
    recipients = fields.List(fields.Nested(PackRecipientSchema()), required=True)


async def store_key_pair(
    *,
    storage: BaseStorage,
    public_key: bytes,
    secret_key: bytes,
    key_type: KeyType,
    metadata: dict,
    tags={},
):
    """Store signing key pair in storage.

    Args:
        storage (BaseStorage): [description]
        public_key (bytes): [description]
        secret_key (bytes): [description]
        key_type (KeyType): [description]
        metadata (dict): [description]
    """
    verkey = bytes_to_b58(public_key)
    data = {
        "verkey": verkey,
        "secret_key": bytes_to_b58(secret_key),
        "key_type": key_type.key_type,
        "metadata": metadata,
    }
    record = StorageRecord(
        "key_pair",
        json.dumps(data),
        {**tags, "verkey": verkey, "key_type": key_type.key_type},
        uuid.uuid4().hex,
    )

    await storage.add_record(record)


async def get_key_pair(*, storage: BaseStorage, verkey: str) -> dict:
    """Retrieve signing key pair from storage by verkey.

    Args:
        storage (BaseStorage): The storage to use for querying
        verkey (str): The verkey to query for

    Raises:
        StorageDuplicateError: If more than one key pair is found for this verkey
        StorageNotFoundError: If no key pair is found for this verkey

    Returns
        dict: The key pair data

    """

    record = await storage.find_record("key_pair", {"verkey": verkey})
    data = json.loads(record.value)

    return data


async def get_key_pairs(
    *, storage: BaseStorage, tag_query: Optional[Mapping] = None
) -> List[dict]:
    records: Sequence[StorageRecord] = await storage.find_all_records(
        "key_pair", tag_query
    )

    return [json.loads(record.value) for record in records]


async def update_key_pair_metadata(
    *, storage: BaseStorage, verkey: str, metadata: dict
):
    record = await storage.find_record("key_pair", {"verkey": verkey})
    data = json.loads(record.value)
    data["metadata"] = metadata

    await storage.update_record(record, json.dumps(data), record.tags)


def create_keypair(key_type: KeyType, seed: bytes = None) -> Tuple[bytes, bytes]:
    """
    Create a public and private keypair from a seed value.

    Args:
        key_type: The type of key to generate
        seed: Seed for keypair

    Raises:
        WalletError: If the key type is not supported

    Returns:
        A tuple of (public key, secret key)

    """
    if key_type == KeyType.ED25519:
        return create_ed25519_keypair(seed)
    elif key_type == KeyType.BLS12381G2:
        return create_bls12381g2_keypair(seed)
    else:
        raise WalletError(f"Unsupported key type: {key_type.key_type}")


def create_ed25519_keypair(seed: bytes = None) -> Tuple[bytes, bytes]:
    """
    Create a public and private ed25519 keypair from a seed value.

    Args:
        seed: Seed for keypair

    Returns:
        A tuple of (public key, secret key)

    """
    if not seed:
        seed = random_seed()
    pk, sk = nacl.bindings.crypto_sign_seed_keypair(seed)
    return pk, sk


def create_bls12381g2_keypair(seed: bytes = None) -> Tuple[bytes, bytes]:
    """
    Create a public and private bls12381g2 keypair from a seed value.

    Args:
        seed: Seed for keypair

    Returns:
        A tuple of (public key, secret key)

    """
    if not seed:
        seed = random_seed()

    key_pair = BlsKeyPair.generate_g2(seed)
    return key_pair.public_key, key_pair.secret_key


def random_seed() -> bytes:
    """
    Generate a random seed value.

    Returns:
        A new random seed

    """
    return nacl.utils.random(nacl.bindings.crypto_box_SEEDBYTES)


def seed_to_did(seed: str) -> str:
    """
    Derive a DID from a seed value.

    Args:
        seed: The seed to derive

    Returns:
        The DID derived from the seed

    """
    seed = validate_seed(seed)
    verkey, _ = create_ed25519_keypair(seed)
    did = bytes_to_b58(verkey[:16])
    return did


def sign_pk_from_sk(secret: bytes) -> bytes:
    """Extract the verkey from a secret signing key."""
    seed_len = nacl.bindings.crypto_sign_SEEDBYTES
    return secret[seed_len:]


def validate_seed(seed: Union[str, bytes]) -> bytes:
    """
    Convert a seed parameter to standard format and check length.

    Args:
        seed: The seed to validate

    Returns:
        The validated and encoded seed

    """
    if not seed:
        return None
    if isinstance(seed, str):
        if "=" in seed:
            seed = b64_to_bytes(seed)
        else:
            seed = seed.encode("ascii")
    if not isinstance(seed, bytes):
        raise WalletError("Seed value is not a string or bytes")
    if len(seed) != 32:
        raise WalletError("Seed value must be 32 bytes in length")
    return seed


def sign_message(
    message: Union[List[bytes], bytes], secret: bytes, key_type: KeyType
) -> bytes:
    """
    Sign message(s) using a private signing key.

    Args:
        message: The message(s) to sign
        secret: The private signing key
        key_type: The key type to derive the signature algorithm from

    Returns:
        bytes: The signature

    """
    # Make messages list if not already for easier checking going forward
    messages = message if isinstance(message, list) else [message]

    if key_type == KeyType.ED25519:
        if len(messages) > 1:
            raise WalletError("ed25519 can only sign a single message")

        return sign_message_ed25519(
            message=messages[0],
            secret=secret,
        )
    elif key_type == KeyType.BLS12381G2:
        return sign_messages_bls12381g2(messages=messages, secret=secret)
    else:
        raise WalletError(f"Unsupported key type: {key_type.key_type}")


def sign_message_ed25519(message: bytes, secret: bytes) -> bytes:
    """Sign message using a ed25519 private signing key.

    Args:
        messages (bytes): The message to sign
        secret (bytes): The private signing key

    Returns:
        bytes: The signature

    """
    result = nacl.bindings.crypto_sign(message, secret)
    sig = result[: nacl.bindings.crypto_sign_BYTES]
    return sig


def sign_messages_bls12381g2(messages: List[bytes], secret: bytes):
    """Sign messages using a bls12381g2 private signing key.

    Args:
        messages (List[bytes]): The messages to sign
        secret (bytes): The private signing key

    Returns:
        bytes: The signature

    """
    key_pair = BlsKeyPair.from_secret_key(secret)

    messages = [message.decode("utf-8") for message in messages]

    sign_request = SignRequest(key_pair=key_pair, messages=messages)

    return bbs_sign(sign_request)


def verify_signed_message(
    message: Union[List[bytes], bytes],
    signature: bytes,
    verkey: bytes,
    key_type: KeyType,
) -> bool:
    """
    Verify a signed message according to a public verification key.

    Args:
        message: The message(s) to verify
        signature: The signature to verify
        verkey: The verkey to use in verification
        key_type: The key type to derive the signature verification algorithm from

    Returns:
        True if verified, else False

    """
    # Make messages list if not already for easier checking going forward
    messages = message if isinstance(message, list) else [message]

    if key_type == KeyType.ED25519:
        if len(messages) > 1:
            raise WalletError("ed25519 can only verify a single message")

        return verify_signed_message_ed25519(
            message=messages[0], signature=signature, verkey=verkey
        )
    elif key_type == KeyType.BLS12381G2:
        return verify_signed_messages_bls12381g2(
            messages=messages, signature=signature, public_key=verkey
        )
    else:
        raise WalletError(f"Unsupported key type: {key_type.key_type}")


def verify_signed_message_ed25519(
    message: bytes, signature: bytes, verkey: bytes
) -> bool:
    """
    Verify an ed25519 signed message according to a public verification key.

    Args:
        message: The message to verify
        signature: The signature to verify
        verkey: The verkey to use in verification

    Returns:
        True if verified, else False

    """
    try:
        nacl.bindings.crypto_sign_open(signature + message, verkey)
    except nacl.exceptions.BadSignatureError:
        return False
    return True


def verify_signed_messages_bls12381g2(
    messages: List[bytes], signature: bytes, public_key: bytes
) -> bool:
    """
    Verify an ed25519 signed message according to a public verification key.

    Args:
        signed: The signed messages
        public_key: The public key to use in verification

    Returns:
        True if verified, else False

    """
    key_pair = BlsKeyPair(public_key=public_key)
    messages = [message.decode("utf-8") for message in messages]

    verify_request = VerifyRequest(
        key_pair=key_pair, signature=signature, messages=messages
    )

    return bbs_verify(verify_request)


def prepare_pack_recipient_keys(
    to_verkeys: Sequence[bytes], from_secret: bytes = None
) -> Tuple[str, bytes]:
    """
    Assemble the recipients block of a packed message.

    Args:
        to_verkeys: Verkeys of recipients
        from_secret: Secret to use for signing keys

    Returns:
        A tuple of (json result, key)

    """
    cek = nacl.bindings.crypto_secretstream_xchacha20poly1305_keygen()
    recips = []

    for target_vk in to_verkeys:
        target_pk = nacl.bindings.crypto_sign_ed25519_pk_to_curve25519(target_vk)
        if from_secret:
            sender_pk = sign_pk_from_sk(from_secret)
            sender_vk = bytes_to_b58(sender_pk).encode("ascii")
            enc_sender = nacl.bindings.crypto_box_seal(sender_vk, target_pk)
            sk = nacl.bindings.crypto_sign_ed25519_sk_to_curve25519(from_secret)

            nonce = nacl.utils.random(nacl.bindings.crypto_box_NONCEBYTES)
            enc_cek = nacl.bindings.crypto_box(cek, nonce, target_pk, sk)
        else:
            enc_sender = None
            nonce = None
            enc_cek = nacl.bindings.crypto_box_seal(cek, target_pk)

        recips.append(
            OrderedDict(
                [
                    ("encrypted_key", bytes_to_b64(enc_cek, urlsafe=True)),
                    (
                        "header",
                        OrderedDict(
                            [
                                ("kid", bytes_to_b58(target_vk)),
                                (
                                    "sender",
                                    bytes_to_b64(enc_sender, urlsafe=True)
                                    if enc_sender
                                    else None,
                                ),
                                (
                                    "iv",
                                    bytes_to_b64(nonce, urlsafe=True)
                                    if nonce
                                    else None,
                                ),
                            ]
                        ),
                    ),
                ]
            )
        )

    data = OrderedDict(
        [
            ("enc", "xchacha20poly1305_ietf"),
            ("typ", "JWM/1.0"),
            ("alg", "Authcrypt" if from_secret else "Anoncrypt"),
            ("recipients", recips),
        ]
    )
    return json.dumps(data), cek


# def locate_pack_recipient_key(
#     recipients: Sequence[dict], find_key: Callable
# ) -> Tuple[bytes, str, str]:
#     """
#     Locate pack recipient key.

#     Decode the encryption key and sender verification key from a
#     corresponding recipient block, if any is defined.

#     Args:
#         recipients: Recipients to locate
#         find_key: Function used to find private key

#     Returns:
#         A tuple of (cek, sender_vk, recip_vk_b58)

#     Raises:
#         ValueError: If no corresponding recipient key found

#     """
#     not_found = []
#     for recip in recipients:
#         if not recip or "header" not in recip or "encrypted_key" not in recip:
#             raise ValueError("Invalid recipient header")

#         recip_vk_b58 = recip["header"].get("kid")
#         secret = find_key(recip_vk_b58)
#         if secret is None:
#             not_found.append(recip_vk_b58)
#             continue
#         recip_vk = b58_to_bytes(recip_vk_b58)
#         pk = nacl.bindings.crypto_sign_ed25519_pk_to_curve25519(recip_vk)
#         sk = nacl.bindings.crypto_sign_ed25519_sk_to_curve25519(secret)

#         encrypted_key = b64_to_bytes(recip["encrypted_key"], urlsafe=True)

#         nonce_b64 = recip["header"].get("iv")
#         nonce = b64_to_bytes(nonce_b64, urlsafe=True) if nonce_b64 else None
#         sender_b64 = recip["header"].get("sender")
#         enc_sender = b64_to_bytes(sender_b64, urlsafe=True) if sender_b64 else None

#         if nonce and enc_sender:
#             sender_vk_bin = nacl.bindings.crypto_box_seal_open(enc_sender, pk, sk)
#             sender_vk = sender_vk_bin.decode("ascii")
#             sender_pk = nacl.bindings.crypto_sign_ed25519_pk_to_curve25519(
#                 b58_to_bytes(sender_vk_bin)
#             )
#             cek = nacl.bindings.crypto_box_open(encrypted_key, nonce, sender_pk, sk)
#         else:
#             sender_vk = None
#             cek = nacl.bindings.crypto_box_seal_open(encrypted_key, pk, sk)
#         return cek, sender_vk, recip_vk_b58
#     raise ValueError("No corresponding recipient key found in {}".format(not_found))


def ed25519_pk_to_curve25519(public_key: bytes) -> bytes:
    """Covert a public Ed25519 key to a public Curve25519 key as bytes."""
    return nacl.bindings.crypto_sign_ed25519_pk_to_curve25519(public_key)


def encrypt_plaintext(
    message: str, add_data: bytes, key: bytes
) -> Tuple[bytes, bytes, bytes]:
    """
    Encrypt the payload of a packed message.

    Args:
        message: Message to encrypt
        add_data:
        key: Key used for encryption

    Returns:
        A tuple of (ciphertext, nonce, tag)

    """
    nonce = nacl.utils.random(nacl.bindings.crypto_aead_chacha20poly1305_ietf_NPUBBYTES)
    message_bin = message.encode("ascii")
    output = nacl.bindings.crypto_aead_chacha20poly1305_ietf_encrypt(
        message_bin, add_data, nonce, key
    )
    mlen = len(message)
    ciphertext = output[:mlen]
    tag = output[mlen:]
    return ciphertext, nonce, tag


def decrypt_plaintext(
    ciphertext: bytes, recips_bin: bytes, nonce: bytes, key: bytes
) -> str:
    """
    Decrypt the payload of a packed message.

    Args:
        ciphertext:
        recips_bin:
        nonce:
        key:

    Returns:
        The decrypted string

    """
    output = nacl.bindings.crypto_aead_chacha20poly1305_ietf_decrypt(
        ciphertext, recips_bin, nonce, key
    )
    return output.decode("ascii")


def encode_pack_message(
    message: str, to_verkeys: Sequence[bytes], from_secret: bytes = None
) -> bytes:
    """
    Assemble a packed message for a set of recipients, optionally including the sender.

    Args:
        message: The message to pack
        to_verkeys: The verkeys to pack the message for
        from_secret: The sender secret

    Returns:
        The encoded message

    """
    recips_json, cek = prepare_pack_recipient_keys(to_verkeys, from_secret)
    recips_b64 = bytes_to_b64(recips_json.encode("ascii"), urlsafe=True)

    ciphertext, nonce, tag = encrypt_plaintext(message, recips_b64.encode("ascii"), cek)

    data = OrderedDict(
        [
            ("protected", recips_b64),
            ("iv", bytes_to_b64(nonce, urlsafe=True)),
            ("ciphertext", bytes_to_b64(ciphertext, urlsafe=True)),
            ("tag", bytes_to_b64(tag, urlsafe=True)),
        ]
    )
    return json.dumps(data).encode("ascii")


def decode_pack_message(
    enc_message: bytes, find_key: Callable
) -> Tuple[str, Optional[str], str]:
    """
    Decode a packed message.

    Disassemble and unencrypt a packed message, returning the message content,
    verification key of the sender (if available), and verification key of the
    recipient.

    Args:
        enc_message: The encrypted message
        find_key: Function to retrieve private key

    Returns:
        A tuple of (message, sender_vk, recip_vk)

    Raises:
        ValueError: If the packed message is invalid
        ValueError: If the packed message reipients are invalid
        ValueError: If the pack algorithm is unsupported
        ValueError: If the sender's public key was not provided

    """
    wrapper, recips, is_authcrypt = decode_pack_message_outer(enc_message)
    payload_key, sender_vk = None, None
    for recip_vk in recips:
        recip_secret = find_key(recip_vk)
        if recip_secret:
            payload_key, sender_vk = extract_payload_key(recips[recip_vk], recip_secret)
            break

    if not payload_key:
        raise ValueError(
            "No corresponding recipient key found in {}".format(tuple(recips))
        )
    if not sender_vk and is_authcrypt:
        raise ValueError("Sender public key not provided for Authcrypt message")

    message = decode_pack_message_payload(wrapper, payload_key)
    return message, sender_vk, recip_vk


def decode_pack_message_outer(enc_message: bytes) -> Tuple[dict, dict, bool]:
    """
    Decode the outer wrapper of a packed message and extract the recipients.

    Args:
        enc_message: The encrypted message

    Returns: a tuple of the decoded wrapper, recipients, and authcrypt flag

    """
    try:
        wrapper = PackMessageSchema().loads(enc_message)
    except ValidationError:
        raise ValueError("Invalid packed message")

    recips_json = b64_to_bytes(wrapper["protected"], urlsafe=True).decode("ascii")
    try:
        recips_outer = PackRecipientsSchema().loads(recips_json)
    except ValidationError:
        raise ValueError("Invalid packed message recipients")

    alg = recips_outer["alg"]
    is_authcrypt = alg == "Authcrypt"
    if not is_authcrypt and alg != "Anoncrypt":
        raise ValueError("Unsupported pack algorithm: {}".format(alg))

    recips = extract_pack_recipients(recips_outer["recipients"])
    return wrapper, recips, is_authcrypt


def decode_pack_message_payload(wrapper: dict, payload_key: bytes) -> str:
    """
    Decode the payload of a packed message once the CEK is known.

    Args:
        wrapper: The decoded message wrapper
        payload_key: The decrypted payload key

    """
    ciphertext = b64_to_bytes(wrapper["ciphertext"], urlsafe=True)
    nonce = b64_to_bytes(wrapper["iv"], urlsafe=True)
    tag = b64_to_bytes(wrapper["tag"], urlsafe=True)

    payload_bin = ciphertext + tag
    protected_bin = wrapper["protected"].encode("ascii")
    message = decrypt_plaintext(payload_bin, protected_bin, nonce, payload_key)
    return message


def extract_pack_recipients(recipients: Sequence[dict]) -> dict:
    """
    Extract the pack message recipients into a dict indexed by verkey.

    Args:
        recipients: Recipients to locate

    Raises:
        ValueError: If the recipients block is mal-formatted

    """
    result = {}
    for recip in recipients:
        if not recip or "header" not in recip or "encrypted_key" not in recip:
            raise ValueError("Invalid recipient header")

        recip_vk_b58 = recip["header"].get("kid")
        if not recip_vk_b58:
            raise ValueError("Blank recipient key")
        if recip_vk_b58 in result:
            raise ValueError("Duplicate recipient key")

        sender_b64 = recip["header"].get("sender")
        enc_sender = b64_to_bytes(sender_b64, urlsafe=True) if sender_b64 else None

        nonce_b64 = recip["header"].get("iv")
        if sender_b64 and not nonce_b64:
            raise ValueError("Missing iv")
        elif not sender_b64 and nonce_b64:
            raise ValueError("Unexpected iv")
        nonce = b64_to_bytes(nonce_b64, urlsafe=True) if nonce_b64 else None

        encrypted_key = b64_to_bytes(recip["encrypted_key"], urlsafe=True)

        result[recip_vk_b58] = {
            "sender": enc_sender,
            "nonce": nonce,
            "key": encrypted_key,
        }
    return result


def extract_payload_key(sender_cek: dict, recip_secret: bytes) -> Tuple[bytes, str]:
    """
    Extract the payload key from pack recipient details.

    Returns: A tuple of the CEK and sender verkey
    """
    recip_vk = sign_pk_from_sk(recip_secret)
    recip_pk = nacl.bindings.crypto_sign_ed25519_pk_to_curve25519(recip_vk)
    recip_sk = nacl.bindings.crypto_sign_ed25519_sk_to_curve25519(recip_secret)

    if sender_cek["nonce"] and sender_cek["sender"]:
        sender_vk_bin = nacl.bindings.crypto_box_seal_open(
            sender_cek["sender"], recip_pk, recip_sk
        )
        sender_vk = sender_vk_bin.decode("ascii")
        sender_pk = nacl.bindings.crypto_sign_ed25519_pk_to_curve25519(
            b58_to_bytes(sender_vk_bin)
        )
        cek = nacl.bindings.crypto_box_open(
            sender_cek["key"], sender_cek["nonce"], sender_pk, recip_sk
        )
    else:
        sender_vk = None
        cek = nacl.bindings.crypto_box_seal_open(sender_cek["key"], recip_pk, recip_sk)
    return cek, sender_vk
