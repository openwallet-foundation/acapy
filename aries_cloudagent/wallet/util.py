"""Wallet utility functions."""

import re
import base58
import base64
import nacl.utils
import nacl.bindings
import math

from collections import namedtuple
from io import BytesIO
from typing import List, Sequence, Optional
import wallet.constant as constant

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


## MultiHashEncoder support
Multihash = namedtuple("Multihash", "code,name,length,digest")


def coerce_code(hash_fn):
    if isinstance(hash_fn, str):
        try:
            return constant.HASH_CODES[hash_fn]
        except KeyError:
            raise ValueError("Unsupported hash function {}".format(hash_fn))

    elif isinstance(hash_fn, int):
        if hash_fn in constant.CODE_HASHES or (0 < hash_fn < 0x10):
            return hash_fn
        raise ValueError("Unsupported hash code {}".format(hash_fn))

    raise TypeError("hash code should be either an integer or a string")


def multi_hash_encode(digest, code):
    hash_code = coerce_code(code)

    if not isinstance(digest, bytes):
        raise TypeError("digest must be a bytes object, not {}".format(type(digest)))
    length = len(digest)
    return varint.encode(hash_code) + varint.encode(length) + digest


def multi_hash_decode(multihash):
    if not isinstance(multihash, bytes):
        raise TypeError("multihash should be bytes, not {}", type(multihash))

    if len(multihash) < 3:
        raise ValueError("multihash must be greater than 3 bytes.")

    buffer = BytesIO(multihash)
    try:
        code = varint.decode_stream(buffer)
    except TypeError:
        raise ValueError("Invalid varint provided")

    if not is_valid_code(code):
        raise ValueError("Unsupported hash code {}".format(code))

    try:
        length = varint.decode_stream(buffer)
    except TypeError:
        raise ValueError("Invalid length provided")

    buf = buffer.read()

    if len(buf) != length:
        raise ValueError(
            "Inconsistent multihash length {} != {}".format(len(buf), length)
        )

    return Multihash(
        code=code, name=constant.CODE_HASHES.get(code, code), length=length, digest=buf
    )


def multi_hash_is_valid_code(code):
    return (0 < code < 0x10) or code in constant.CODE_HASHES


## MultiBaseEncoder support [Base58]
def multi_base_encode(buffer: bytes) -> str:
    base58_encoded = bytes_to_b58(buffer)
    return f"z{base58_encoded}"


def multi_base_decode(data: str) -> bytes:
    base58_decoded = b58_to_bytes(data[1:])
    return base58_decoded


## Derive X25519 from Ed25519 keys
## With no addition of external library or
## dependancy [like numpy, libsodium, etc.]
## Ref: https://github.com/StableLib/stablelib/blob/master/packages/ed25519/ed25519.ts
def gf(init: Optional[List] = None):
    r = [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    ]
    idx = 0
    if init:
        while idx < len(init):
            r[idx] = init[idx]
            idx = idx + 1
    return r


D = gf(
    [
        0x78A3,
        0x1359,
        0x4DCA,
        0x75EB,
        0xD8AB,
        0x4141,
        0x0A4D,
        0x0070,
        0xE898,
        0x7779,
        0x4079,
        0x8CC7,
        0xFE73,
        0x2B6F,
        0x6CEE,
        0x5203,
    ]
)

D2 = gf(
    [
        0xF159,
        0x26B2,
        0x9B94,
        0xEBD6,
        0xB156,
        0x8283,
        0x149A,
        0x00E0,
        0xD130,
        0xEEF3,
        0x80F2,
        0x198E,
        0xFCE7,
        0x56DF,
        0xD9DC,
        0x2406,
    ]
)

X = gf(
    [
        0xD51A,
        0x8F25,
        0x2D60,
        0xC956,
        0xA7B2,
        0x9525,
        0xC760,
        0x692C,
        0xDC5C,
        0xFDD6,
        0xE231,
        0xC0A4,
        0x53FE,
        0xCD6E,
        0x36D3,
        0x2169,
    ]
)

Y = gf(
    [
        0x6658,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
        0x6666,
    ]
)

I = gf(
    [
        0xA0B0,
        0x4A0E,
        0x1B27,
        0xC4EE,
        0xE478,
        0xAD2F,
        0x1806,
        0x2F43,
        0xD7A7,
        0x3DFB,
        0x0099,
        0x2B4D,
        0xDF0B,
        0x4FC1,
        0x2480,
        0x2B83,
    ]
)


def set25519(r: List, a: List):
    idx = 0
    while idx < 16:
        r[idx] = a[idx] or 0
        idx = idx + 1


def car25519(o: List):
    idx = 0
    c = 1
    while idx < 16:
        v = o[idx] + c + 65535
        c = math.floor(v / 65536)
        o[idx] = v - c * 65536
        idx = idx + 1
    o[0] += c - 1 + 37 * (c - 1)


def sel25519(p: List, q: List, b):
    c = round(b - 1)
    idx = 0
    while idx < 16:
        t = c & (int(p[idx]) ^ int(q[idx]))
        p[idx] = int(p[idx]) ^ t
        q[idx] = int(q[idx]) ^ t
        idx = idx + 1


def pack25519(o: List, n: List):
    m = gf()
    t = gf()
    idx = 0
    while idx < 16:
        t[idx] = n[idx]
        idx = idx + 1
    car25519(t)
    car25519(t)
    car25519(t)
    j = 0
    while j < 2:
        m[0] = t[0] - 0xFFED
        i = 1
        while i < 15:
            m[i] = t[i] - 0xFFFF - ((int(m[i - 1]) >> 16) & 1)
            m[i - 1] = int(m[i - 1]) & 0xFFFF
            i = i + 1
        m[15] = t[15] - 0x7FFF - ((int(m[14]) >> 16) & 1)
        b = (int(m[15]) >> 16) & 1
        m[14] = int(m[14]) & 0xFFFF
        sel25519(t, m, 1 - b)
        j = j + 1
    k = 0
    while k < 16:
        o[2 * k] = int(t[k]) & 0xFF
        o[2 * k + 1] = int(t[k]) >> 8
        k = k + 1


def verify32(x: List, y: List):
    d = 0
    idx = 0
    while idx < 32:
        d |= x[idx] ^ y[idx]
        idx = idx + 1
    # This was unsigned right shift
    return (1 & ((d - 1) >> 8)) - 1


def neq25519(a: List, b: List):
    c = [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    ]
    d = [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    ]
    pack25519(c, a)
    pack25519(d, b)
    return verify32(c, d)


def par25519(a: List):
    d = [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    ]
    pack25519(d, a)
    return d[0] & 1


def unpack25519(o: List, n: List):
    idx = 0
    while idx < 16:
        o[idx] = n[2 * idx] + (n[2 * idx + 1] << 8)
        idx = idx + 1
    o[15] &= 0x7FFF


def add(o: List, a: List, b: List):
    idx = 0
    while idx < 16:
        o[idx] = a[idx] + b[idx]
        idx = idx + 1


def sub(o: List, a: List, b: List):
    idx = 0
    while idx < 16:
        o[idx] = a[idx] - b[idx]
        idx = idx + 1


def mul(o: List, a: List, b: List):
    v = None
    c = None
    t0 = 0
    t1 = 0
    t2 = 0
    t3 = 0
    t4 = 0
    t5 = 0
    t6 = 0
    t7 = 0
    t8 = 0
    t9 = 0
    t10 = 0
    t11 = 0
    t12 = 0
    t13 = 0
    t14 = 0
    t15 = 0
    t16 = 0
    t17 = 0
    t18 = 0
    t19 = 0
    t20 = 0
    t21 = 0
    t22 = 0
    t23 = 0
    t24 = 0
    t25 = 0
    t26 = 0
    t27 = 0
    t28 = 0
    t29 = 0
    t30 = 0
    b0 = b[0]
    b1 = b[1]
    b2 = b[2]
    b3 = b[3]
    b4 = b[4]
    b5 = b[5]
    b6 = b[6]
    b7 = b[7]
    b8 = b[8]
    b9 = b[9]
    b10 = b[10]
    b11 = b[11]
    b12 = b[12]
    b13 = b[13]
    b14 = b[14]
    b15 = b[15]
    v = a[0]
    t0 += v * b0
    t1 += v * b1
    t2 += v * b2
    t3 += v * b3
    t4 += v * b4
    t5 += v * b5
    t6 += v * b6
    t7 += v * b7
    t8 += v * b8
    t9 += v * b9
    t10 += v * b10
    t11 += v * b11
    t12 += v * b12
    t13 += v * b13
    t14 += v * b14
    t15 += v * b15
    v = a[1]
    t1 += v * b0
    t2 += v * b1
    t3 += v * b2
    t4 += v * b3
    t5 += v * b4
    t6 += v * b5
    t7 += v * b6
    t8 += v * b7
    t9 += v * b8
    t10 += v * b9
    t11 += v * b10
    t12 += v * b11
    t13 += v * b12
    t14 += v * b13
    t15 += v * b14
    t16 += v * b15
    v = a[2]
    t2 += v * b0
    t3 += v * b1
    t4 += v * b2
    t5 += v * b3
    t6 += v * b4
    t7 += v * b5
    t8 += v * b6
    t9 += v * b7
    t10 += v * b8
    t11 += v * b9
    t12 += v * b10
    t13 += v * b11
    t14 += v * b12
    t15 += v * b13
    t16 += v * b14
    t17 += v * b15
    v = a[3]
    t3 += v * b0
    t4 += v * b1
    t5 += v * b2
    t6 += v * b3
    t7 += v * b4
    t8 += v * b5
    t9 += v * b6
    t10 += v * b7
    t11 += v * b8
    t12 += v * b9
    t13 += v * b10
    t14 += v * b11
    t15 += v * b12
    t16 += v * b13
    t17 += v * b14
    t18 += v * b15
    v = a[4]
    t4 += v * b0
    t5 += v * b1
    t6 += v * b2
    t7 += v * b3
    t8 += v * b4
    t9 += v * b5
    t10 += v * b6
    t11 += v * b7
    t12 += v * b8
    t13 += v * b9
    t14 += v * b10
    t15 += v * b11
    t16 += v * b12
    t17 += v * b13
    t18 += v * b14
    t19 += v * b15
    v = a[5]
    t5 += v * b0
    t6 += v * b1
    t7 += v * b2
    t8 += v * b3
    t9 += v * b4
    t10 += v * b5
    t11 += v * b6
    t12 += v * b7
    t13 += v * b8
    t14 += v * b9
    t15 += v * b10
    t16 += v * b11
    t17 += v * b12
    t18 += v * b13
    t19 += v * b14
    t20 += v * b15
    v = a[6]
    t6 += v * b0
    t7 += v * b1
    t8 += v * b2
    t9 += v * b3
    t10 += v * b4
    t11 += v * b5
    t12 += v * b6
    t13 += v * b7
    t14 += v * b8
    t15 += v * b9
    t16 += v * b10
    t17 += v * b11
    t18 += v * b12
    t19 += v * b13
    t20 += v * b14
    t21 += v * b15
    v = a[7]
    t7 += v * b0
    t8 += v * b1
    t9 += v * b2
    t10 += v * b3
    t11 += v * b4
    t12 += v * b5
    t13 += v * b6
    t14 += v * b7
    t15 += v * b8
    t16 += v * b9
    t17 += v * b10
    t18 += v * b11
    t19 += v * b12
    t20 += v * b13
    t21 += v * b14
    t22 += v * b15
    v = a[8]
    t8 += v * b0
    t9 += v * b1
    t10 += v * b2
    t11 += v * b3
    t12 += v * b4
    t13 += v * b5
    t14 += v * b6
    t15 += v * b7
    t16 += v * b8
    t17 += v * b9
    t18 += v * b10
    t19 += v * b11
    t20 += v * b12
    t21 += v * b13
    t22 += v * b14
    t23 += v * b15
    v = a[9]
    t9 += v * b0
    t10 += v * b1
    t11 += v * b2
    t12 += v * b3
    t13 += v * b4
    t14 += v * b5
    t15 += v * b6
    t16 += v * b7
    t17 += v * b8
    t18 += v * b9
    t19 += v * b10
    t20 += v * b11
    t21 += v * b12
    t22 += v * b13
    t23 += v * b14
    t24 += v * b15
    v = a[10]
    t10 += v * b0
    t11 += v * b1
    t12 += v * b2
    t13 += v * b3
    t14 += v * b4
    t15 += v * b5
    t16 += v * b6
    t17 += v * b7
    t18 += v * b8
    t19 += v * b9
    t20 += v * b10
    t21 += v * b11
    t22 += v * b12
    t23 += v * b13
    t24 += v * b14
    t25 += v * b15
    v = a[11]
    t11 += v * b0
    t12 += v * b1
    t13 += v * b2
    t14 += v * b3
    t15 += v * b4
    t16 += v * b5
    t17 += v * b6
    t18 += v * b7
    t19 += v * b8
    t20 += v * b9
    t21 += v * b10
    t22 += v * b11
    t23 += v * b12
    t24 += v * b13
    t25 += v * b14
    t26 += v * b15
    v = a[12]
    t12 += v * b0
    t13 += v * b1
    t14 += v * b2
    t15 += v * b3
    t16 += v * b4
    t17 += v * b5
    t18 += v * b6
    t19 += v * b7
    t20 += v * b8
    t21 += v * b9
    t22 += v * b10
    t23 += v * b11
    t24 += v * b12
    t25 += v * b13
    t26 += v * b14
    t27 += v * b15
    v = a[13]
    t13 += v * b0
    t14 += v * b1
    t15 += v * b2
    t16 += v * b3
    t17 += v * b4
    t18 += v * b5
    t19 += v * b6
    t20 += v * b7
    t21 += v * b8
    t22 += v * b9
    t23 += v * b10
    t24 += v * b11
    t25 += v * b12
    t26 += v * b13
    t27 += v * b14
    t28 += v * b15
    v = a[14]
    t14 += v * b0
    t15 += v * b1
    t16 += v * b2
    t17 += v * b3
    t18 += v * b4
    t19 += v * b5
    t20 += v * b6
    t21 += v * b7
    t22 += v * b8
    t23 += v * b9
    t24 += v * b10
    t25 += v * b11
    t26 += v * b12
    t27 += v * b13
    t28 += v * b14
    t29 += v * b15
    v = a[15]
    t15 += v * b0
    t16 += v * b1
    t17 += v * b2
    t18 += v * b3
    t19 += v * b4
    t20 += v * b5
    t21 += v * b6
    t22 += v * b7
    t23 += v * b8
    t24 += v * b9
    t25 += v * b10
    t26 += v * b11
    t27 += v * b12
    t28 += v * b13
    t29 += v * b14
    t30 += v * b15

    t0 += 38 * t16
    t1 += 38 * t17
    t2 += 38 * t18
    t3 += 38 * t19
    t4 += 38 * t20
    t5 += 38 * t21
    t6 += 38 * t22
    t7 += 38 * t23
    t8 += 38 * t24
    t9 += 38 * t25
    t10 += 38 * t26
    t11 += 38 * t27
    t12 += 38 * t28
    t13 += 38 * t29
    t14 += 38 * t30
    c = 1
    v = t0 + c + 65535
    c = math.floor(v / 65536)
    t0 = v - c * 65536
    v = t1 + c + 65535
    c = math.floor(v / 65536)
    t1 = v - c * 65536
    v = t2 + c + 65535
    c = math.floor(v / 65536)
    t2 = v - c * 65536
    v = t3 + c + 65535
    c = math.floor(v / 65536)
    t3 = v - c * 65536
    v = t4 + c + 65535
    c = math.floor(v / 65536)
    t4 = v - c * 65536
    v = t5 + c + 65535
    c = math.floor(v / 65536)
    t5 = v - c * 65536
    v = t6 + c + 65535
    c = math.floor(v / 65536)
    t6 = v - c * 65536
    v = t7 + c + 65535
    c = math.floor(v / 65536)
    t7 = v - c * 65536
    v = t8 + c + 65535
    c = math.floor(v / 65536)
    t8 = v - c * 65536
    v = t9 + c + 65535
    c = math.floor(v / 65536)
    t9 = v - c * 65536
    v = t10 + c + 65535
    c = math.floor(v / 65536)
    t10 = v - c * 65536
    v = t11 + c + 65535
    c = math.floor(v / 65536)
    t11 = v - c * 65536
    v = t12 + c + 65535
    c = math.floor(v / 65536)
    t12 = v - c * 65536
    v = t13 + c + 65535
    c = math.floor(v / 65536)
    t13 = v - c * 65536
    v = t14 + c + 65535
    c = math.floor(v / 65536)
    t14 = v - c * 65536
    v = t15 + c + 65535
    c = math.floor(v / 65536)
    t15 = v - c * 65536
    t0 += c - 1 + 37 * (c - 1)

    c = 1
    v = t0 + c + 65535
    c = math.floor(v / 65536)
    t0 = v - c * 65536
    v = t1 + c + 65535
    c = math.floor(v / 65536)
    t1 = v - c * 65536
    v = t2 + c + 65535
    c = math.floor(v / 65536)
    t2 = v - c * 65536
    v = t3 + c + 65535
    c = math.floor(v / 65536)
    t3 = v - c * 65536
    v = t4 + c + 65535
    c = math.floor(v / 65536)
    t4 = v - c * 65536
    v = t5 + c + 65535
    c = math.floor(v / 65536)
    t5 = v - c * 65536
    v = t6 + c + 65535
    c = math.floor(v / 65536)
    t6 = v - c * 65536
    v = t7 + c + 65535
    c = math.floor(v / 65536)
    t7 = v - c * 65536
    v = t8 + c + 65535
    c = math.floor(v / 65536)
    t8 = v - c * 65536
    v = t9 + c + 65535
    c = math.floor(v / 65536)
    t9 = v - c * 65536
    v = t10 + c + 65535
    c = math.floor(v / 65536)
    t10 = v - c * 65536
    v = t11 + c + 65535
    c = math.floor(v / 65536)
    t11 = v - c * 65536
    v = t12 + c + 65535
    c = math.floor(v / 65536)
    t12 = v - c * 65536
    v = t13 + c + 65535
    c = math.floor(v / 65536)
    t13 = v - c * 65536
    v = t14 + c + 65535
    c = math.floor(v / 65536)
    t14 = v - c * 65536
    v = t15 + c + 65535
    c = math.floor(v / 65536)
    t15 = v - c * 65536
    t0 += c - 1 + 37 * (c - 1)

    o[0] = t0
    o[1] = t1
    o[2] = t2
    o[3] = t3
    o[4] = t4
    o[5] = t5
    o[6] = t6
    o[7] = t7
    o[8] = t8
    o[9] = t9
    o[10] = t10
    o[11] = t11
    o[12] = t12
    o[13] = t13
    o[14] = t14
    o[15] = t15


def square(o: List, a: List):
    mul(o, a, a)


def inv25519(o: List, i: List):
    c = gf()
    l = 0
    while l < 16:
        c[l] = i[l]
        l = l + 1
    m = 253
    while m >= 0:
        square(c, c)
        if m != 2 and m != 4:
            mul(c, c, i)
        m = m - 1
    n = 0
    while n < 16:
        o[n] = c[n]
        n = n + 1


def pow2523(o: List, i: List):
    c = gf()
    l = 0
    while l < 16:
        c[l] = i[l]
        l = l + 1
    m = 250
    while m >= 0:
        square(c, c)
        if m != 1:
            mul(c, c, i)
        m = m - 1
    n = 0
    while n < 16:
        o[n] = c[n]
        n = n + 1


def unpackneg(r: Sequence, p: List):
    t = gf()
    chk = gf()
    num = gf()
    den = gf()
    den2 = gf()
    den4 = gf()
    den6 = gf()

    set25519(r[2], gf([1]))
    unpack25519(r[1], p)
    square(num, r[1])
    mul(den, num, D)
    sub(num, num, r[2])
    add(den, r[2], den)

    square(den2, den)
    square(den4, den2)
    mul(den6, den4, den2)
    mul(t, den6, num)
    mul(t, t, den)

    pow2523(t, t)
    mul(t, t, num)
    mul(t, t, den)
    mul(t, t, den)
    mul(r[0], t, den)

    square(chk, r[0])
    mul(chk, chk, den)
    if neq25519(chk, num):
        mul(r[0], r[0], I)

    square(chk, r[0])
    mul(chk, chk, den)
    if neq25519(chk, num):
        return -1

    if par25519(r[0]) == (p[31] >> 7):
        sub(r[0], gf(), r[0])

    mul(r[3], r[0], r[1])
    return 0


def convertPublicKeyToX25519(pk: bytes):
    public_key_list = list(bytearray(pk))
    q = [gf(), gf(), gf(), gf()]

    if unpackneg(q, public_key_list):
        raise ValueError("Ed25519: invalid public key")

    # Formula: montgomeryX = (edwardsY + 1)*inverse(1 - edwardsY) mod p
    a = gf()
    b = gf()
    y = q[1]
    add(a, gf([1]), y)
    sub(b, gf([1]), y)
    inv25519(b, b)
    mul(a, a, b)

    z = [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    ]
    pack25519(z, a)
    return bytes(bytearray(z))
