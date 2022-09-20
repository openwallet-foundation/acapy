"""Did method enum."""

from typing import Dict, List, Mapping, Optional
from .error import BaseError
from .key_type import KeyType


class DIDMethod:
    """Class to represent a did method."""

    def __init__(self, name, key_types, rotation) -> None:
        self._method_name: str = name
        self._supported_key_types: List[KeyType] = key_types
        self._supports_rotation: bool = rotation

    @property
    def method_name(self):
        """Get method name."""
        return self._method_name

    @property
    def supports_rotation(self):
        """Check rotation support."""
        return self._supports_rotation

    @property
    def supported_key_types(self):
        """Get supported key types."""
        return self._supported_key_types

    def supports_key_type(self, key_type: KeyType) -> bool:
        """Check whether the current method supports the key type."""
        return key_type in self.supported_key_types


class DIDMethods:
    """DID Method class specifying DID methods with supported key types."""

    def __init__(self) -> None:
        self._registry: Dict[str, DIDMethod] = {}

    def registered(self, method: str) -> bool:
        """Check for a supported method."""
        return method in list(self._registry.items())

    def register(self, method: DIDMethod):
        """Registers a new did method."""
        self._registry[method.method_name] = method

    def from_method(self, method_name: str) -> Optional[DIDMethod]:
        """Retrieve a did method from method name."""
        method: DIDMethod = self._registry[method_name]
        if method:
            return method
        raise BaseError(f"Unsupported did method: {method_name}")

    def from_metadata(self, metadata: Mapping) -> Optional[DIDMethod]:
        """Get DID method instance from metadata object.

        Returns SOV if no metadata was found for backwards compatibility.
        """
        method_name: str = metadata.get("method", "sov")
        return self.from_method(method_name)

    def from_did(self, did: str) -> Optional[DIDMethod]:
        """Get DID method instance from the did url."""
        method_name = did.split(":")[1] if did.startswith("did:") else "sov"
        return self.from_method(method_name)
