"""Wallet utility functions."""

import re

import base58
import base64

import nacl.utils
import nacl.bindings

from ..core.profile import Profile


def random_seed() -> bytes:
    """
    Generate a random seed value.

    Returns:
        A new random seed

    """
    return nacl.utils.random(nacl.bindings.crypto_box_SEEDBYTES)


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


def bytes_to_b64(val: bytes, urlsafe=False, pad=True, encoding: str = "ascii") -> str:
    """Convert a byte string to base 64."""
    b64 = (
        base64.urlsafe_b64encode(val).decode(encoding)
        if urlsafe
        else base64.b64encode(val).decode(encoding)
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
    """Given a DID and abbreviated verkey, return the full verkey."""
    return (
        bytes_to_b58(b58_to_bytes(did.split(":")[-1]) + b58_to_bytes(abbr_verkey[1:]))
        if abbr_verkey.startswith("~")
        else abbr_verkey
    )


def default_did_from_verkey(verkey: str) -> str:
    """Given a verkey, return the default indy did.

    By default the did is the first 16 bytes of the verkey.
    """
    did = bytes_to_b58(b58_to_bytes(verkey)[:16])
    return did


def abbr_verkey(full_verkey: str, did: str = None) -> str:
    """Given a full verkey and DID, return the abbreviated verkey."""
    did_len = len(b58_to_bytes(did.split(":")[-1])) if did else 16
    return f"~{bytes_to_b58(b58_to_bytes(full_verkey)[did_len:])}"


DID_EVENT_PREFIX = "acapy::ENDORSE_DID::"
DID_ATTRIB_EVENT_PREFIX = "acapy::ENDORSE_DID_ATTRIB::"
EVENT_LISTENER_PATTERN = re.compile(f"^{DID_EVENT_PREFIX}(.*)?$")
ATTRIB_EVENT_LISTENER_PATTERN = re.compile(f"^{DID_ATTRIB_EVENT_PREFIX}(.*)?$")


async def notify_endorse_did_event(profile: Profile, did: str, meta_data: dict):
    """Send notification for a DID post-process event."""
    await profile.notify(
        DID_EVENT_PREFIX + did,
        meta_data,
    )


async def notify_endorse_did_attrib_event(profile: Profile, did: str, meta_data: dict):
    """Send notification for a DID ATTRIB post-process event."""
    await profile.notify(
        DID_ATTRIB_EVENT_PREFIX + did,
        meta_data,
    )
