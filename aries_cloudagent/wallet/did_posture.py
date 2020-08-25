"""Ledger utilities."""

from enum import Enum
from typing import Mapping, Union


class DIDPosture(Enum):
    """Enum for DID postures: public, posted but not public, local to wallet."""

    PUBLIC = "public"
    POSTED = "posted"
    LOCAL = "local"

    @staticmethod
    def get(posture: Union[str, Mapping]) -> "DIDPosture":
        """Return enum instance corresponding to input string."""
        if posture is None:
            return None

        elif isinstance(posture, str):
            for did_posture in DIDPosture:
                if posture.lower() == did_posture.value:
                    return did_posture

        elif posture.get("public"):
            return DIDPosture.PUBLIC
        elif posture.get("posted"):
            return DIDPosture.POSTED
        elif isinstance(posture, Mapping):
            return DIDPosture.LOCAL

        return None
