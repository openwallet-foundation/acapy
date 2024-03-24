"""DIDComm prefix management."""

import re

from enum import Enum

QUALIFIED = re.compile(r"^[a-zA-Z\-\+]+:.+")


def qualify(msg_type: str, prefix: str):
    """Qualify a message type with a prefix, if unqualified."""

    return msg_type if QUALIFIED.match(msg_type or "") else f"{prefix}/{msg_type}"


class DIDCommPrefix(Enum):
    """Enum for DIDComm Prefix, old or new style, per Aries RFC 384."""

    NEW = "https://didcomm.org"
    OLD = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec"

    def qualify(self, msg_type: str) -> str:
        """Qualify input message type with prefix and separator."""

        return qualify(msg_type, self.value)

    @classmethod
    def qualify_all(cls, messages: dict) -> dict:
        """Apply all known prefixes to a dictionary of message types."""

        return {qualify(k, pfx.value): v for pfx in cls for k, v in messages.items()}

    @staticmethod
    def qualify_current(slug: str) -> str:
        """Qualify input slug with prefix currently in effect and separator.

        This method now will always use the new prefix.
        """

        return qualify(slug, DIDCommPrefix.NEW.value)

    @staticmethod
    def unqualify(qual: str) -> str:
        """Strip prefix and separator from input, if present, and return result."""
        for pfx in DIDCommPrefix:
            if (qual or "").startswith(f"{pfx.value}/"):
                return qual.split(f"{pfx.value}/")[1]

        return qual
