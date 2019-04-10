"""Issuer utils."""

from hashlib import sha256
from typing import Any

I32_BOUND = 2 ** 31


def encode(orig: Any) -> str:
    """
    Encode a credential value as an int.

    Encode credential attribute value, purely stringifying any int32
    and leaving numeric int32 strings alone, but mapping any other
    input to a stringified 256-bit (but not 32-bit) integer.
    Predicates in indy-sdk operate
    on int32 values properly only when their encoded values match their raw values.

    Args:
        orig: original value to encode

    Returns:
        encoded value

    """

    if isinstance(orig, int) and -I32_BOUND <= orig < I32_BOUND:
        return str(int(orig))  # python bools are ints

    try:
        i32orig = int(str(orig))  # don't encode floats as ints
        if -I32_BOUND <= i32orig < I32_BOUND:
            return str(i32orig)
    except (ValueError, TypeError):
        pass

    rv = int.from_bytes(sha256(str(orig).encode()).digest(), "big")
    while -I32_BOUND <= rv < I32_BOUND:
        rv = int.from_bytes(
            sha256(rv.encode()).digest(), "big"
        )  # sha256 maps no 32-bit int to another: terminates

    return str(rv)
