"""DIDComm v1 envelope handling via Askar backend."""

from collections import OrderedDict
from typing import Optional, Sequence, Tuple

from aries_askar import (
    crypto_box,
    Key,
    KeyAlg,
    Session,
)
from aries_askar.bindings import key_get_secret_bytes
from marshmallow import ValidationError

from ...utils.jwe import b64url, JweEnvelope, JweRecipient
from ...wallet.base import WalletError
from ...wallet.crypto import extract_pack_recipients
from ...wallet.util import b58_to_bytes, bytes_to_b58


def pack_message(
    to_verkeys: Sequence[str], from_key: Optional[Key], message: bytes
) -> bytes:
    """Encode a message using the DIDComm v1 'pack' algorithm."""
    wrapper = JweEnvelope(with_protected_recipients=True, with_flatten_recipients=False)
    cek = Key.generate(KeyAlg.C20P)
    # avoid converting to bytes object: this way the only copy is zeroed afterward
    cek_b = key_get_secret_bytes(cek._handle)
    sender_vk = (
        bytes_to_b58(from_key.get_public_bytes()).encode("utf-8") if from_key else None
    )
    sender_xk = from_key.convert_key(KeyAlg.X25519) if from_key else None

    for target_vk in to_verkeys:
        target_xk = Key.from_public_bytes(
            KeyAlg.ED25519, b58_to_bytes(target_vk)
        ).convert_key(KeyAlg.X25519)
        if sender_vk:
            enc_sender = crypto_box.crypto_box_seal(target_xk, sender_vk)
            nonce = crypto_box.random_nonce()
            enc_cek = crypto_box.crypto_box(target_xk, sender_xk, cek_b, nonce)
            wrapper.add_recipient(
                JweRecipient(
                    encrypted_key=enc_cek,
                    header=OrderedDict(
                        [
                            ("kid", target_vk),
                            ("sender", b64url(enc_sender)),
                            ("iv", b64url(nonce)),
                        ]
                    ),
                )
            )
        else:
            enc_sender = None
            nonce = None
            enc_cek = crypto_box.crypto_box_seal(target_xk, cek_b)
            wrapper.add_recipient(
                JweRecipient(encrypted_key=enc_cek, header={"kid": target_vk})
            )
    wrapper.set_protected(
        OrderedDict(
            [
                ("enc", "xchacha20poly1305_ietf"),
                ("typ", "JWM/1.0"),
                ("alg", "Authcrypt" if from_key else "Anoncrypt"),
            ]
        ),
    )
    enc = cek.aead_encrypt(message, aad=wrapper.protected_bytes)
    ciphertext, tag, nonce = enc.parts
    wrapper.set_payload(ciphertext, nonce, tag)
    return wrapper.to_json().encode("utf-8")


async def unpack_message(session: Session, enc_message: bytes) -> Tuple[str, str, str]:
    """Decode a message using the DIDComm v1 'unpack' algorithm."""
    try:
        wrapper = JweEnvelope.from_json(enc_message)
    except ValidationError:
        raise WalletError("Invalid packed message")

    alg = wrapper.protected.get("alg")
    is_authcrypt = alg == "Authcrypt"
    if not is_authcrypt and alg != "Anoncrypt":
        raise WalletError("Unsupported pack algorithm: {}".format(alg))

    recips = extract_pack_recipients(wrapper.recipients)

    payload_key, sender_vk = None, None
    for recip_vk in recips:
        recip_key_entry = await session.fetch_key(recip_vk)
        if recip_key_entry:
            payload_key, sender_vk = _extract_payload_key(
                recips[recip_vk], recip_key_entry.key
            )
            break

    if not payload_key:
        raise WalletError(
            "No corresponding recipient key found in {}".format(tuple(recips))
        )
    if not sender_vk and is_authcrypt:
        raise WalletError("Sender public key not provided for Authcrypt message")

    cek = Key.from_secret_bytes(KeyAlg.C20P, payload_key)
    message = cek.aead_decrypt(
        wrapper.ciphertext,
        nonce=wrapper.iv,
        tag=wrapper.tag,
        aad=wrapper.protected_bytes,
    )
    return message, recip_vk, sender_vk


def _extract_payload_key(sender_cek: dict, recip_secret: Key) -> Tuple[bytes, str]:
    """
    Extract the payload key from pack recipient details.

    Returns: A tuple of the CEK and sender verkey
    """
    recip_x = recip_secret.convert_key(KeyAlg.X25519)

    if sender_cek["nonce"] and sender_cek["sender"]:
        sender_vk = crypto_box.crypto_box_seal_open(
            recip_x, sender_cek["sender"]
        ).decode("utf-8")
        sender_x = Key.from_public_bytes(
            KeyAlg.ED25519, b58_to_bytes(sender_vk)
        ).convert_key(KeyAlg.X25519)
        cek = crypto_box.crypto_box_open(
            recip_x, sender_x, sender_cek["key"], sender_cek["nonce"]
        )
    else:
        sender_vk = None
        cek = crypto_box.crypto_box_seal_open(recip_x, sender_cek["key"])
    return cek, sender_vk
