"""Wallet utility functions."""

import base58
import base64

from multicodec import add_prefix, remove_prefix


def pad(val: str) -> str:
    """Pad base64 values if need be: JWT calls to omit trailing padding."""
    padlen = 4 - len(val) % 4
    return val if padlen > 2 else (val + "=" * padlen)


def unpad(val: str) -> str:
    """Remove padding from base64 values if need be."""
    return val.rstrip("=")


def b64_to_bytes(val: str, urlsafe=False) -> bytes:
    """Convert a base 64 string to bytes."""
    if urlsafe:
        return base64.urlsafe_b64decode(pad(val))
    return base64.b64decode(pad(val))


def b64_to_str(val: str, urlsafe=False, encoding=None) -> str:
    """Convert a base 64 string to string on input encoding (default utf-8)."""
    return b64_to_bytes(val, urlsafe).decode(encoding or "utf-8")


def bytes_to_b64(val: bytes, urlsafe=False, pad=True) -> str:
    """Convert a byte string to base 64."""
    b64 = (
        base64.urlsafe_b64encode(val).decode("ascii")
        if urlsafe
        else base64.b64encode(val).decode("ascii")
    )
    return b64 if pad else unpad(b64)


def str_to_b64(val: str, urlsafe=False, encoding=None, pad=True) -> str:
    """Convert a string to base64 string on input encoding (default utf-8)."""
    return bytes_to_b64(val.encode(encoding or "utf-8"), urlsafe, pad)


def set_urlsafe_b64(val: str, urlsafe: bool = True) -> str:
    """Set URL safety in base64 encoding."""
    if urlsafe:
        return val.replace("+", "-").replace("/", "_")
    return val.replace("-", "+").replace("_", "/")


def b58_to_bytes(val: str) -> bytes:
    """Convert a base 58 string to bytes."""
    return base58.b58decode(val)


def bytes_to_b58(val: bytes) -> str:
    """Convert a byte string to base 58."""
    return base58.b58encode(val).decode("ascii")


def full_verkey(did: str, abbr_verkey: str) -> str:
    """Given a DID and a short verkey, return the full verkey."""
    return (
        bytes_to_b58(b58_to_bytes(did.split(":")[-1]) + b58_to_bytes(abbr_verkey[1:]))
        if abbr_verkey.startswith("~")
        else abbr_verkey
    )


def naked_to_did_key(key: str) -> str:
    """Convert a naked ed25519 verkey to W3C did:key format."""
    key_bytes = b58_to_bytes(key)
    prefixed_key_bytes = add_prefix("ed25519-pub", key_bytes)
    did_key = f"did:key:z{bytes_to_b58(prefixed_key_bytes)}"
    return did_key


def did_key_to_naked(did_key: str) -> str:
    """Convert a W3C did:key to naked ed25519 verkey format."""
    stripped_key = did_key.split("did:key:z").pop()
    stripped_key_bytes = b58_to_bytes(stripped_key)
    naked_key_bytes = remove_prefix(stripped_key_bytes)
    return bytes_to_b58(naked_key_bytes)
