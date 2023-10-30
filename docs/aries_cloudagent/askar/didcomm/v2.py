"""DIDComm v2 envelope handling via Askar backend."""

import json

from collections import OrderedDict
from typing import Mapping, Tuple, Union

from aries_askar import ecdh, AskarError, Key, KeyAlg, Session
from marshmallow import ValidationError

from ...utils.jwe import b64url, from_b64url, JweEnvelope, JweRecipient
from ...wallet.base import WalletError


class DidcommEnvelopeError(WalletError):
    """A base error class for DIDComm envelope wrapping and unwrapping operations."""


def ecdh_es_encrypt(to_verkeys: Mapping[str, Key], message: bytes) -> bytes:
    """Encode a message using DIDComm v2 anonymous encryption."""
    wrapper = JweEnvelope(with_flatten_recipients=False)

    alg_id = "ECDH-ES+A256KW"
    enc_id = "XC20P"
    enc_alg = KeyAlg.XC20P
    wrap_alg = KeyAlg.A256KW

    if not to_verkeys:
        raise DidcommEnvelopeError("No message recipients")

    try:
        cek = Key.generate(enc_alg)
    except AskarError:
        raise DidcommEnvelopeError("Error creating content encryption key")

    for kid, recip_key in to_verkeys.items():
        try:
            epk = Key.generate(recip_key.algorithm, ephemeral=True)
        except AskarError:
            raise DidcommEnvelopeError("Error creating ephemeral key")
        enc_key = ecdh.EcdhEs(alg_id, None, None).sender_wrap_key(
            wrap_alg, epk, recip_key, cek
        )
        wrapper.add_recipient(
            JweRecipient(
                encrypted_key=enc_key.ciphertext,
                header={"kid": kid, "epk": epk.get_jwk_public()},
            )
        )

    wrapper.set_protected(
        OrderedDict(
            [
                ("alg", alg_id),
                ("enc", enc_id),
            ]
        )
    )
    try:
        payload = cek.aead_encrypt(message, aad=wrapper.protected_bytes)
    except AskarError:
        raise DidcommEnvelopeError("Error encrypting message payload")
    wrapper.set_payload(payload.ciphertext, payload.nonce, payload.tag)

    return wrapper.to_json().encode("utf-8")


def ecdh_es_decrypt(
    wrapper: JweEnvelope,
    recip_kid: str,
    recip_key: Key,
) -> bytes:
    """Decode a message with DIDComm v2 anonymous encryption."""

    alg_id = wrapper.protected.get("alg")
    if alg_id in ("ECDH-ES+A128KW", "ECDH-ES+A256KW"):
        wrap_alg = alg_id[8:]
    else:
        raise DidcommEnvelopeError(f"Unsupported ECDH-ES algorithm: {alg_id}")

    recip = wrapper.get_recipient(recip_kid)
    if not recip:
        raise DidcommEnvelopeError(f"Recipient header not found: {recip_kid}")

    enc_alg = recip.header.get("enc")
    if enc_alg not in ("A128GCM", "A256GCM", "A128CBC-HS256", "A256CBC-HS512", "XC20P"):
        raise DidcommEnvelopeError(f"Unsupported ECDH-ES content encryption: {enc_alg}")

    try:
        epk = Key.from_jwk(recip.header.get("epk"))
    except AskarError:
        raise DidcommEnvelopeError("Error loading ephemeral key")

    apu = recip.header.get("apu")
    apv = recip.header.get("apv")

    try:
        cek = ecdh.EcdhEs(alg_id, apu, apv).receiver_unwrap_key(
            wrap_alg,
            enc_alg,
            epk,
            recip_key,
            recip.encrypted_key,
        )
    except AskarError:
        raise DidcommEnvelopeError("Error decrypting content encryption key")

    try:
        plaintext = cek.aead_decrypt(
            wrapper.ciphertext,
            nonce=wrapper.iv,
            tag=wrapper.tag,
            aad=wrapper.combined_aad,
        )
    except AskarError:
        raise DidcommEnvelopeError("Error decrypting message payload")

    return plaintext


def ecdh_1pu_encrypt(
    to_verkeys: Mapping[str, Key], sender_kid: str, sender_key: Key, message: bytes
) -> bytes:
    """Encode a message using DIDComm v2 authenticated encryption."""
    wrapper = JweEnvelope(with_flatten_recipients=False)

    alg_id = "ECDH-1PU+A256KW"
    enc_id = "A256CBC-HS512"
    enc_alg = KeyAlg.A256CBC_HS512
    wrap_alg = KeyAlg.A256KW
    agree_alg = sender_key.algorithm

    if not to_verkeys:
        raise DidcommEnvelopeError("No message recipients")

    try:
        cek = Key.generate(enc_alg)
    except AskarError:
        raise DidcommEnvelopeError("Error creating content encryption key")

    try:
        epk = Key.generate(agree_alg, ephemeral=True)
    except AskarError:
        raise DidcommEnvelopeError("Error creating ephemeral key")

    apu = b64url(sender_kid)
    apv = []
    for kid, recip_key in to_verkeys.items():
        if agree_alg:
            if agree_alg != recip_key.algorithm:
                raise DidcommEnvelopeError("Recipient key types must be consistent")
        else:
            agree_alg = recip_key.algorithm
        apv.append(kid)
    apv.sort()
    apv = b64url(".".join(apv))

    wrapper.set_protected(
        OrderedDict(
            [
                ("alg", alg_id),
                ("enc", enc_id),
                ("apu", apu),
                ("apv", apv),
                ("epk", json.loads(epk.get_jwk_public())),
                ("skid", sender_kid),
            ]
        )
    )
    try:
        payload = cek.aead_encrypt(message, aad=wrapper.protected_bytes)
    except AskarError:
        raise DidcommEnvelopeError("Error encrypting message payload")
    wrapper.set_payload(payload.ciphertext, payload.nonce, payload.tag)

    for kid, recip_key in to_verkeys.items():
        enc_key = ecdh.Ecdh1PU(alg_id, apu, apv).sender_wrap_key(
            wrap_alg, epk, sender_key, recip_key, cek, cc_tag=payload.tag
        )
        wrapper.add_recipient(
            JweRecipient(encrypted_key=enc_key.ciphertext, header={"kid": kid})
        )

    return wrapper.to_json().encode("utf-8")


def ecdh_1pu_decrypt(
    wrapper: JweEnvelope,
    recip_kid: str,
    recip_key: Key,
    sender_key: Key,
) -> Tuple[str, str, str]:
    """Decode a message with DIDComm v2 authenticated encryption."""

    alg_id = wrapper.protected.get("alg")
    if alg_id in ("ECDH-1PU+A128KW", "ECDH-1PU+A256KW"):
        wrap_alg = alg_id[9:]
    else:
        raise DidcommEnvelopeError(f"Unsupported ECDH-1PU algorithm: {alg_id}")

    enc_alg = wrapper.protected.get("enc")
    if enc_alg not in ("A128CBC-HS256", "A256CBC-HS512"):
        raise DidcommEnvelopeError(
            f"Unsupported ECDH-1PU content encryption: {enc_alg}"
        )

    recip = wrapper.get_recipient(recip_kid)
    if not recip:
        raise DidcommEnvelopeError(f"Recipient header not found: {recip_kid}")

    try:
        epk = Key.from_jwk(wrapper.protected.get("epk"))
    except AskarError:
        raise DidcommEnvelopeError("Error loading ephemeral key")

    apu = wrapper.protected.get("apu")
    apv = wrapper.protected.get("apv")

    try:
        cek = ecdh.Ecdh1PU(alg_id, apu, apv).receiver_unwrap_key(
            wrap_alg,
            enc_alg,
            epk,
            sender_key,
            recip_key,
            recip.encrypted_key,
            cc_tag=wrapper.tag,
        )
    except AskarError:
        raise DidcommEnvelopeError("Error decrypting content encryption key")

    try:
        plaintext = cek.aead_decrypt(
            wrapper.ciphertext,
            nonce=wrapper.iv,
            tag=wrapper.tag,
            aad=wrapper.combined_aad,
        )
    except AskarError:
        raise DidcommEnvelopeError("Error decrypting message payload")

    return plaintext


async def unpack_message(
    session: Session, enc_message: Union[bytes, str]
) -> Tuple[str, str, str]:
    """Decode a message using DIDComm v2 encryption."""
    try:
        wrapper = JweEnvelope.from_json(enc_message)
    except ValidationError:
        raise DidcommEnvelopeError("Invalid packed message")

    alg = wrapper.protected.get("alg")
    method = next((m for m in ("ECDH-1PU", "ECDH-ES") if m in alg), None)
    if not method:
        raise DidcommEnvelopeError(f"Unsupported DIDComm encryption algorithm: {alg}")

    sender_key = None
    sender_kid = None
    recip_key = None
    recip_kid = None
    for kid in wrapper.recipient_key_ids:
        recip_key_entry = next(
            iter(await session.fetch_all_keys(tag_filter={"kid": kid})), None
        )
        if recip_key_entry:
            recip_kid = kid
            recip_key = recip_key_entry.key
            break

    if not recip_key:
        raise DidcommEnvelopeError("No recognized recipient key")

    if method == "ECDH-1PU":
        sender_kid_apu = None
        apu = wrapper.protected.get("apu")
        if apu:
            try:
                sender_kid_apu = from_b64url(apu).decode("utf-8")
            except (UnicodeDecodeError, ValidationError):
                raise DidcommEnvelopeError("Invalid apu value")
        sender_kid = wrapper.protected.get("skid") or sender_kid_apu
        if sender_kid_apu and sender_kid != sender_kid_apu:
            raise DidcommEnvelopeError("Mismatch between skid and apu")
        if not sender_kid:
            raise DidcommEnvelopeError("Sender key ID not provided")
        # FIXME - validate apv if present?
        # FIXME - will need to insert proper sender key resolution method here
        # instead of looking in the wallet
        sender_key_entry = next(
            iter(await session.fetch_all_keys(tag_filter={"kid": sender_kid})), None
        )
        if not sender_key_entry:
            raise DidcommEnvelopeError("Sender public key not found")
        sender_key = sender_key_entry.key
        plaintext = ecdh_1pu_decrypt(wrapper, recip_kid, recip_key, sender_key)
    else:
        plaintext = ecdh_es_decrypt(wrapper, recip_kid, recip_key)

    return plaintext, recip_kid, sender_kid
