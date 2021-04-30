"""Did method enum."""

from typing import List, Mapping, NamedTuple, Optional
from enum import Enum

from .key_type import KeyType
from .error import BaseError

DIDMethodSpec = NamedTuple(
    "DIDMethodSpec",
    [
        ("method_name", str),
        ("supported_key_types", List[KeyType]),
        ("supports_rotation", bool),
    ],
)


class DIDMethod(Enum):
    """DID Method class specifying DID methods with supported key types."""

    SOV = DIDMethodSpec(
        method_name="sov", supported_key_types=[KeyType.ED25519], supports_rotation=True
    )
    KEY = DIDMethodSpec(
        method_name="key",
        supported_key_types=[KeyType.ED25519, KeyType.BLS12381G2],
        supports_rotation=False,
    )

    @property
    def method_name(self) -> str:
        """Getter for did method name. e.g. sov or key."""
        return self.value.method_name

    @property
    def supported_key_types(self) -> List[KeyType]:
        """Getter for supported key types of method."""
        return self.value.supported_key_types

    @property
    def supports_rotation(self) -> bool:
        """Check whether the current method supports key rotation."""
        return self.value.supports_rotation

    def supports_key_type(self, key_type: KeyType) -> bool:
        """Check whether the current method supports the key type."""
        return key_type in self.supported_key_types

    def from_metadata(metadata: Mapping) -> "DIDMethod":
        """Get DID method instance from metadata object.

        Returns SOV if no metadata was found for backwards compatability.
        """
        method = metadata.get("method")

        # extract from metadata object
        if method:
            for did_method in DIDMethod:
                if method == did_method.method_name:
                    return did_method

        # return default SOV for backward compat
        return DIDMethod.SOV

    def from_method(method: str) -> Optional["DIDMethod"]:
        """Get DID method instance from the method name."""
        for did_method in DIDMethod:
            if method == did_method.method_name:
                return did_method

        return None

    def from_did(did: str) -> "DIDMethod":
        """Get DID method instance from the method name."""
        if not did.startswith("did:"):
            # sov has no prefix
            return DIDMethod.SOV

        parts = did.split(":")
        method_str = parts[1]

        method = DIDMethod.from_method(method_str)

        if not method:
            raise BaseError(f"Unsupported did method: {method_str}")

        return method
