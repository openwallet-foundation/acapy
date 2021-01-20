"""Base Class for DID Resolvers."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Sequence

from .diddoc import ResolvedDIDDoc


class BaseDIDResolver(ABC):
    """Base Class for DID Resolvers."""

    class Type(Enum):
        """Resolver Type declarations."""

        NATIVE = "native"
        NON_NATIVE = "non-native"

    def __init__(self, type_: Type = None):
        """Initialize BaseDIDResolver.

        Args:
            type_ (Type): Type of resolver, native or non-native
        """
        self.type = type_ or self.Type.NON_NATIVE

    @property
    def native(self):
        """Return if this resolver is native."""
        return self.type == self.Type.NATIVE

    @property
    @abstractmethod
    def supported_methods(self) -> Sequence[str]:
        """Return list of DID methods supported by this resolver."""

    def supports(self, method: str):
        """Return if this resolver supports the given method."""
        return method in self.supported_methods

    @abstractmethod
    def resolve(self, did: str) -> ResolvedDIDDoc:
        """Resolve a DID using this resolver."""
