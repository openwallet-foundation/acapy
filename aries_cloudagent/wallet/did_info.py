"""KeyInfo, DIDInfo."""

from collections import namedtuple

KeyInfo = namedtuple("KeyInfo", "verkey metadata")
DIDInfo = namedtuple("DIDInfo", "did verkey metadata")
