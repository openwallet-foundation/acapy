"""Ledger utilities."""

from collections import namedtuple
from enum import Enum
from typing import Mapping, Union

DIDPostureSpec = namedtuple("DIDPostureSpec", "moniker ordinal public posted")


class DIDPosture(Enum):
    """Enum for DID postures: public, posted but not public, or in wallet only."""

    PUBLIC = DIDPostureSpec("public", 0, True, True)
    POSTED = DIDPostureSpec("posted", 1, False, True)
    WALLET_ONLY = DIDPostureSpec("wallet_only", 2, False, False)

    @staticmethod
    def get(posture: Union[str, Mapping]) -> "DIDPosture":
        """Return enum instance corresponding to input string or DID metadata."""
        if posture is None:
            return None

        elif isinstance(posture, str):
            for did_posture in DIDPosture:
                if posture.lower() == did_posture.value.moniker:
                    return did_posture

        elif posture.get("public"):
            return DIDPosture.PUBLIC
        elif posture.get("posted"):
            return DIDPosture.POSTED
        elif isinstance(posture, Mapping):
            return DIDPosture.WALLET_ONLY

        return None

    @property
    def moniker(self) -> str:
        """Name for DID posture."""
        return self.value.moniker

    @property
    def metadata(self) -> Mapping:
        """DID metadata for DID posture."""
        return {"public": self.value.public, "posted": self.value.posted}

    @property
    def ordinal(self) -> Mapping:
        """Ordinal for presentation: public first, then posted and wallet-only."""
        return self.value.ordinal
