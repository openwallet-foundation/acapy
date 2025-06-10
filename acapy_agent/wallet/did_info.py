"""KeyInfo, DIDInfo."""

from typing import NamedTuple, Union, List, Optional

from .did_method import DIDMethod
from .key_type import KeyType

INVITATION_REUSE_KEY = "invitation_reuse"


class KeyInfo(NamedTuple):
    """Class returning key information."""

    verkey: str
    metadata: dict
    key_type: KeyType
    kid: Optional[Union[List[str], str]] = None


DIDInfo = NamedTuple(
    "DIDInfo",
    [
        ("did", str),
        ("verkey", str),
        ("metadata", dict),
        ("method", DIDMethod),
        ("key_type", KeyType),
    ],
)
