"""Functions for performing Key Agreement."""

import hashlib

from binascii import unhexlify
from typing import Union

from ecdsa import ECDH, NIST256p


def derive_shared_secret(private_key: bytes, public_key: bytes):
    """Generate a shared secret from keys in byte format."""

    derive = ECDH(curve=NIST256p)
    derive.load_private_key_bytes(unhexlify(private_key))
    derive.load_received_public_key_bytes(unhexlify(public_key))

    secret = derive.generate_sharedsecret_bytes()
    return secret


def derive_shared_secret_from_key(private_key, public_key):
    """Generate a shared secret from keys in ecdsa.Keys format."""

    derive = ECDH(curve=NIST256p)
    derive.load_private_key(private_key)
    derive.load_received_public_key(public_key)

    secret = derive.generate_sharedsecret_bytes()
    return secret


def _to_bytes(s: Union[str, bytes]) -> bytes:
    if isinstance(s, str):
        return s.encode("utf-8")
    return s


def concat_kdf(
    shared_secret: bytes,
    alg: Union[str, bytes],
    apu: Union[str, bytes],
    apv: Union[str, bytes],
    keydatalen: int,
):
    """Generate a shared encryption key from a shared secret."""

    alg = _to_bytes(alg)
    apu = _to_bytes(apu)
    apv = _to_bytes(apv)

    # ECDH-1PU requires a "round number 1" to be prefixed onto the shared secret z
    hasher = hashlib.sha256((1).to_bytes(4, "big"))
    # Ze + Zs
    hasher.update(shared_secret)
    # AlgId
    hasher.update(len(alg).to_bytes(4, "big"))
    hasher.update(alg)
    # PartyUInfo
    hasher.update(len(apu).to_bytes(4, "big"))
    hasher.update(apu)
    # PartyVInfo
    hasher.update(len(apv).to_bytes(4, "big"))
    hasher.update(apv)
    # SuppPubInfo
    hasher.update((keydatalen * 8).to_bytes(4, "big"))

    return hasher.digest()
