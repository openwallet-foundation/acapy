"""Multicodec wrap and unwrap functions."""

from enum import Enum
from typing import Literal, NamedTuple, Optional, Union


class Multicodec(NamedTuple):
    """Multicodec base class."""

    name: str
    code: bytes


class SupportedCodecs(Enum):
    """Enumeration of supported multicodecs."""

    ed25519_pub = Multicodec("ed25519-pub", b"\xed\x01")
    x25519_pub = Multicodec("x25519-pub", b"\xec\x01")
    bls12381g1 = Multicodec("bls12_381-g1-pub", b"\xea\x01")
    bls12381g2 = Multicodec("bls12_381-g2-pub", b"\xeb\x01")
    bls12381g1g2 = Multicodec("bls12_381-g1g2-pub", b"\xee\x01")
    secp256k1_pub = Multicodec("secp256k1-pub", b"\xe7\x01")

    @classmethod
    def by_name(cls, name: str) -> Multicodec:
        """Get multicodec by name."""
        for codec in cls:
            if codec.value.name == name:
                return codec.value
        raise ValueError(f"Unsupported multicodec: {name}")

    @classmethod
    def for_data(cls, data: bytes) -> Multicodec:
        """Get multicodec by data."""
        for codec in cls:
            if data.startswith(codec.value.code):
                return codec.value
        raise ValueError("Unsupported multicodec")


MulticodecStr = Literal[
    "ed25519-pub",
    "x25519-pub",
    "bls12_381-g1-pub",
    "bls12_381-g2-pub",
    "bls12_381-g1g2-pub",
    "secp256k1-pub",
]


def multicodec(name: str) -> Multicodec:
    """Get multicodec by name."""
    return SupportedCodecs.by_name(name)


def wrap(multicodec: Union[Multicodec, MulticodecStr], data: bytes) -> bytes:
    """Wrap data with multicodec prefix."""
    if isinstance(multicodec, str):
        multicodec = SupportedCodecs.by_name(multicodec)
    elif isinstance(multicodec, Multicodec):
        pass
    else:
        raise TypeError("multicodec must be Multicodec or MulticodecStr")

    return multicodec.code + data


def unwrap(data: bytes, codec: Optional[Multicodec] = None) -> tuple[Multicodec, bytes]:
    """Unwrap data with multicodec prefix."""
    if not codec:
        codec = SupportedCodecs.for_data(data)
    return codec, data[len(codec.code) :]
