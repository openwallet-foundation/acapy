"""
Cryptography functions used by BasicWallet
"""

from collections import OrderedDict
import json
from typing import Callable, Optional, Sequence

from marshmallow import fields, Schema, ValidationError
import msgpack
import pysodium

from .error import WalletError
from .util import bytes_to_b58, bytes_to_b64, b64_to_bytes, b58_to_bytes


class PackMessageSchema(Schema):
    protected = fields.Str(required=True)
    iv = fields.Str(required=True)
    tag = fields.Str(required=True)
    ciphertext = fields.Str(required=True)


class PackRecipientHeaderSchema(Schema):
    kid = fields.Str(required=True)
    sender = fields.Str(required=False, allow_none=True)
    iv = fields.Str(required=False, allow_none=True)


class PackRecipientSchema(Schema):
    encrypted_key = fields.Str(required=True)
    header = fields.Nested(PackRecipientHeaderSchema(), required=True)


class PackRecipientsSchema(Schema):
    enc = fields.Constant("xchacha20poly1305_ietf", required=True)
    typ = fields.Constant("JWM/1.0", required=True)
    alg = fields.Str(required=True)
    recipients = fields.List(fields.Nested(PackRecipientSchema()), required=True)


def create_keypair(seed: bytes = None) -> (bytes, bytes):
    """Create a public and private signing keypair from a seed value"""
    if not seed:
        seed = random_seed()
    pk, sk = pysodium.crypto_sign_seed_keypair(seed)
    return pk, sk


def random_seed() -> bytes:
    """Generate a random seed value"""
    return pysodium.randombytes(pysodium.crypto_secretbox_KEYBYTES)


def validate_seed(seed: (str, bytes)) -> bytes:
    """Convert a seed parameter to standard format and check length"""
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


def sign_message(message: bytes, secret: bytes) -> bytes:
    """Sign a message using a private signing key"""
    result = pysodium.crypto_sign(message, secret)
    sig = result[: pysodium.crypto_sign_BYTES]
    return sig


def verify_signed_message(signed: bytes, verkey: bytes) -> bool:
    """Verify a signed message according to a public verification key"""
    try:
        pysodium.crypto_sign_open(signed, verkey)
    except ValueError:
        return False
    return True


def anon_crypt_message(message: bytes, to_verkey: bytes) -> bytes:
    """Apply anon_crypt to a binary message"""
    pk = pysodium.crypto_sign_pk_to_box_pk(to_verkey)
    enc_message = pysodium.crypto_box_seal(message, pk)
    return enc_message


def anon_decrypt_message(enc_message: bytes, secret: bytes) -> bytes:
    """Apply anon_decrypt to a binary message"""
    sign_pk, sign_sk = create_keypair(secret)
    pk = pysodium.crypto_sign_pk_to_box_pk(sign_pk)
    sk = pysodium.crypto_sign_sk_to_box_sk(sign_sk)

    message = pysodium.crypto_box_seal_open(enc_message, pk, sk)
    return message


def auth_crypt_message(message: bytes, to_verkey: bytes, from_secret: bytes) -> bytes:
    """Apply auth_crypt to a binary message"""
    nonce = pysodium.randombytes(pysodium.crypto_box_NONCEBYTES)
    target_pk = pysodium.crypto_sign_pk_to_box_pk(to_verkey)
    sender_pk, sender_sk = create_keypair(from_secret)
    sk = pysodium.crypto_sign_sk_to_box_sk(sender_sk)
    enc_body = pysodium.crypto_box(message, nonce, target_pk, sk)
    combo_box = OrderedDict(
        [
            ("msg", bytes_to_b64(enc_body)),
            ("sender", bytes_to_b58(sender_pk)),
            ("nonce", bytes_to_b64(nonce)),
        ]
    )
    combo_box_bin = msgpack.packb(combo_box, use_bin_type=True)
    enc_message = pysodium.crypto_box_seal(combo_box_bin, target_pk)
    return enc_message


def auth_decrypt_message(enc_message: bytes, secret: bytes) -> (bytes, str):
    """Apply auth_decrypt to a binary message"""
    sign_pk, sign_sk = create_keypair(secret)
    pk = pysodium.crypto_sign_pk_to_box_pk(sign_pk)
    sk = pysodium.crypto_sign_sk_to_box_sk(sign_sk)
    body = pysodium.crypto_box_seal_open(enc_message, pk, sk)

    unpacked = msgpack.unpackb(body, raw=False)
    sender_vk = unpacked["sender"]
    nonce = b64_to_bytes(unpacked["nonce"])
    enc_message = b64_to_bytes(unpacked["msg"])
    sender_pk = pysodium.crypto_sign_pk_to_box_pk(b58_to_bytes(sender_vk))
    message = pysodium.crypto_box_open(enc_message, nonce, sender_pk, sk)
    return message, sender_vk


def prepare_pack_recipient_keys(
    to_verkeys: Sequence[bytes], from_secret: bytes = None
) -> (str, bytes):
    """Assemble the recipients block of a packed message"""
    cek = pysodium.crypto_secretstream_xchacha20poly1305_keygen()
    recips = []

    for target_vk in to_verkeys:
        target_pk = pysodium.crypto_sign_pk_to_box_pk(target_vk)
        if from_secret:
            sender_pk, sender_sk = create_keypair(from_secret)
            sender_vk = bytes_to_b58(sender_pk).encode("ascii")
            enc_sender = pysodium.crypto_box_seal(sender_vk, target_pk)
            sk = pysodium.crypto_sign_sk_to_box_sk(sender_sk)

            nonce = pysodium.randombytes(pysodium.crypto_box_NONCEBYTES)
            enc_cek = pysodium.crypto_box(cek, nonce, target_pk, sk)
        else:
            enc_sender = None
            nonce = None
            enc_cek = pysodium.crypto_box_seal(cek, target_pk)

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


def locate_pack_recipient_key(
    recipients: Sequence[dict], find_key: Callable
) -> (bytes, str, str):
    """
    Decode the encryption key and sender verification key from a
    corresponding recipient block, if any is defined
    """
    not_found = []
    for recip in recipients:
        if not recip or "header" not in recip or "encrypted_key" not in recip:
            raise ValueError("Invalid recipient header")

        recip_vk_b58 = recip["header"].get("kid")
        secret = find_key(recip_vk_b58)
        if secret is None:
            not_found.append(recip_vk_b58)
            continue
        recip_vk = b58_to_bytes(recip_vk_b58)
        pk = pysodium.crypto_sign_pk_to_box_pk(recip_vk)
        sk = pysodium.crypto_sign_sk_to_box_sk(secret)

        encrypted_key = b64_to_bytes(recip["encrypted_key"], urlsafe=True)

        nonce_b64 = recip["header"].get("iv")
        nonce = b64_to_bytes(nonce_b64, urlsafe=True) if nonce_b64 else None
        sender_b64 = recip["header"].get("sender")
        enc_sender = b64_to_bytes(sender_b64, urlsafe=True) if sender_b64 else None

        if nonce and enc_sender:
            sender_vk_bin = pysodium.crypto_box_seal_open(enc_sender, pk, sk)
            sender_vk = sender_vk_bin.decode("ascii")
            sender_pk = pysodium.crypto_sign_pk_to_box_pk(b58_to_bytes(sender_vk_bin))
            cek = pysodium.crypto_box_open(encrypted_key, nonce, sender_pk, sk)
        else:
            sender_vk = None
            cek = pysodium.crypto_box_seal_open(encrypted_key, pk, sk)
        return cek, sender_vk, recip_vk_b58
    raise ValueError("No corresponding recipient key found in {}".format(not_found))


def encrypt_plaintext(
    message: str, add_data: bytes, key: bytes
) -> (bytes, bytes, bytes):
    """
    Encrypt the payload of a packed message
    """
    nonce = pysodium.randombytes(pysodium.crypto_aead_chacha20poly1305_ietf_NPUBBYTES)
    message_bin = message.encode("ascii")
    output = pysodium.crypto_aead_chacha20poly1305_ietf_encrypt(
        message_bin, add_data, nonce, key
    )
    mlen = len(message)
    ciphertext = output[:mlen]
    tag = output[mlen:]
    return ciphertext, nonce, tag


def decrypt_plaintext(
    ciphertext: bytes, recips_bin: bytes, nonce: bytes, key: bytes
) -> str:
    """Decrypt the payload of a packed message"""
    output = pysodium.crypto_aead_chacha20poly1305_ietf_decrypt(
        ciphertext, recips_bin, nonce, key
    )
    return output.decode("ascii")


def encode_pack_message(
    message: str, to_verkeys: Sequence[bytes], from_secret: bytes = None
) -> bytes:
    """
    Assemble a packed message for a set of recipients, optionally including the sender
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
) -> (str, Optional[str], str):
    """
    Disassemble and unencrypt a packed message, returning the message content,
    verification key of the sender (if available), and verification key of the recipient
    """
    try:
        wrapper = PackMessageSchema().loads(enc_message)
    except ValidationError:
        raise ValueError("Invalid packed message")

    protected_bin = wrapper["protected"].encode("ascii")
    recips_json = b64_to_bytes(wrapper["protected"], urlsafe=True).decode("ascii")
    print(recips_json)
    try:
        recips_outer = PackRecipientsSchema().loads(recips_json)
    except ValidationError:
        ValueError("Invalid packed message recipients")

    alg = recips_outer["alg"]
    is_authcrypt = alg == "Authcrypt"
    if not is_authcrypt and alg != "Anoncrypt":
        raise ValueError("Unsupported pack algorithm: {}".format(alg))
    cek, sender_vk, recip_vk = locate_pack_recipient_key(
        recips_outer["recipients"], find_key
    )
    if not sender_vk and is_authcrypt:
        raise ValueError("Sender public key not provided for Authcrypt message")

    ciphertext = b64_to_bytes(wrapper["ciphertext"], urlsafe=True)
    nonce = b64_to_bytes(wrapper["iv"], urlsafe=True)
    tag = b64_to_bytes(wrapper["tag"], urlsafe=True)

    payload_bin = ciphertext + tag
    message = decrypt_plaintext(payload_bin, protected_bin, nonce, cek)

    return message, sender_vk, recip_vk
