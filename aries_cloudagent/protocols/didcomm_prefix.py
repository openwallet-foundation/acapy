"""DIDComm prefix management."""

from enum import Enum
from os import environ
from typing import Mapping


class DIDCommPrefix(Enum):
    """Enum for DIDComm Prefix, old or new style, per Aries RFC 384."""

    NEW = "https://didcomm.org"
    OLD = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec"

    @staticmethod
    def set(settings: Mapping):
        """Set current DIDComm prefix value in environment."""

        environ["DIDCOMM_PREFIX"] = (
            DIDCommPrefix.NEW.value
            if settings.get("emit_new_didcomm_prefix")
            else DIDCommPrefix.OLD.value
        )

    def qualify(self, msg_type: str = None) -> str:
        """Qualify input message type with prefix and separator."""

        return f"{self.value}/{msg_type or ''}"

    @staticmethod
    def qualify_current(slug: str = None) -> str:
        """Qualify input slug with prefix currently in effect and separator."""

        return f"{environ.get('DIDCOMM_PREFIX', DIDCommPrefix.NEW.value)}/{slug or ''}"

    @staticmethod
    def unqualify(qual: str) -> str:
        """Strip prefix and separator from input, if present, and return result."""
        for pfx in DIDCommPrefix:
            if (qual or "").startswith(f"{pfx.value}/"):
                return qual.split(f"{pfx.value}/")[1]

        return qual
