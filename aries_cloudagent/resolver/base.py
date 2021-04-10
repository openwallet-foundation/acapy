"""Base Class for DID Resolvers."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Sequence, Union

from pydid import DID, DIDDocument

from ..config.injection_context import InjectionContext
from ..core.error import BaseError
from ..core.profile import Profile


class ResolverError(BaseError):
    """Base class for resolver exceptions."""


class DIDNotFound(ResolverError):
    """Raised when DID is not found in verifiable data registry."""


class DIDMethodNotSupported(ResolverError):
    """Raised when no resolver is registered for a given did method."""


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
    async def setup(self, context: InjectionContext):
        """Do asynchronous resolver setup."""

    @property
    def native(self):
        """Return if this resolver is native."""
        return self.type == ResolverType.NATIVE

    @property
    @abstractmethod
    def supported_methods(self) -> Sequence[str]:
        """Return list of DID methods supported by this resolver."""

    def supports(self, method: str) -> bool:
        """Return if this resolver supports the given method."""
        return method in self.supported_methods

    async def resolve(self, profile: Profile, did: Union[str, DID]) -> DIDDocument:
        """Resolve a DID using this resolver."""
        if isinstance(did, str):
            did = DID(did)

        if not self.supports(did.method):
            raise DIDMethodNotSupported(
                f"{self.__class__.__name__} does not support DID method {did.method}"
            )

        did = str(did)
        did_document = await self._resolve(profile, did)
        result = DIDDocument.deserialize(did_document)
        return result

    @abstractmethod
    async def _resolve(self, profile: Profile, did: DID) -> dict:
        """Resolve a DID using this resolver."""
