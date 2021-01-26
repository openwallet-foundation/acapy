"""Base Class for DID Resolvers."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Sequence

from .diddoc import ResolvedDIDDoc
from ..core.profile import ProfileSession


class ResolverError(Exception):
    """Base class for resolver exceptions."""


class ResolverType(Enum):
    """Resolver Type declarations."""

    NATIVE = "native"
    NON_NATIVE = "non-native"


class BaseDIDResolver(ABC):
    """Base Class for DID Resolvers."""

    def __init__(self, type_: ResolverType = None):
        """Initialize BaseDIDResolver.

        Args:
            type_ (Type): Type of resolver, native or non-native
        """
        self.type = type_ or ResolverType.NON_NATIVE

    @abstractmethod
    async def setup(self, session: ProfileSession):
        """Do asynchronous resolver setup."""

    @property
    def native(self):
        """Return if this resolver is native."""
        return self.type == ResolverType.NATIVE

    @property
    @abstractmethod
    def supported_methods(self) -> Sequence[str]:
        """Return list of DID methods supported by this resolver."""

    def supports(self, method: str):
        """Return if this resolver supports the given method."""
        return method in self.supported_methods

    @abstractmethod
    async def resolve(self, session: ProfileSession, did: str) -> ResolvedDIDDoc:
        """Resolve a DID using this resolver."""
