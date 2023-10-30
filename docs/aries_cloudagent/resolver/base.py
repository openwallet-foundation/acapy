"""Base Class for DID Resolvers."""

from abc import ABC, abstractmethod
from enum import Enum
import re
from typing import NamedTuple, Optional, Pattern, Sequence, Text, Union
import warnings

from pydid import DID

from ..cache.base import BaseCache
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


class ResolutionMetadata(NamedTuple):
    """Resolution Metadata."""

    resolver_type: ResolverType
    resolver: str
    retrieved_time: str
    duration: int

    def serialize(self) -> dict:
        """Return serialized resolution metadata."""
        return {**self._asdict(), "resolver_type": self.resolver_type.value}


class ResolutionResult:
    """Resolution Class to pack the DID Doc and the resolution information."""

    def __init__(self, did_document: dict, metadata: ResolutionMetadata):
        """Initialize Resolution.

        Args:
            did_doc: DID Document resolved
            resolver_metadata: Resolving details
        """
        self.did_document = did_document
        self.metadata = metadata

    def serialize(self) -> dict:
        """Return serialized resolution result."""
        return {
            "did_document": self.did_document,
            "metadata": self.metadata.serialize(),
        }


class BaseDIDResolver(ABC):
    """Base Class for DID Resolvers."""

    DEFAULT_TTL = 3600

    def __init__(self, type_: Optional[ResolverType] = None):
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
    def supported_methods(self) -> Sequence[str]:
        """Return supported methods.

        DEPRECATED: Use supported_did_regex instead.
        """
        return []

    @property
    def supported_did_regex(self) -> Pattern:
        """Supported DID regex for matching this resolver to DIDs it can resolve.

        Override this property with a class var or similar to use regex
        matching on DIDs to determine if this resolver supports a given DID.
        """
        raise NotImplementedError(
            "supported_did_regex must be overriden by subclasses of BaseResolver "
            "to use default supports method"
        )

    async def supports(self, profile: Profile, did: str) -> bool:
        """Return if this resolver supports the given DID.

        Override this method to determine if this resolver supports a DID based
        on information other than just a regular expression; i.e. check a value
        in storage, query a resolver connection record, etc.
        """
        try:
            supported_did_regex = self.supported_did_regex
        except NotImplementedError as error:
            methods = self.supported_methods
            if not methods:
                raise error
            warnings.warn(
                "BaseResolver.supported_methods is deprecated; "
                "use supported_did_regex instead",
                DeprecationWarning,
            )

            supported_did_regex = re.compile(
                "^did:(?:{}):.*$".format("|".join(methods))
            )

        return bool(supported_did_regex.match(did))

    async def resolve(
        self,
        profile: Profile,
        did: Union[str, DID],
        service_accept: Optional[Sequence[Text]] = None,
    ) -> dict:
        """Resolve a DID using this resolver.

        Handles caching of results.
        """
        if isinstance(did, DID):
            did = str(did)
        else:
            DID.validate(did)
        if not await self.supports(profile, did):
            raise DIDMethodNotSupported(
                f"{self.__class__.__name__} does not support DID method for: {did}"
            )

        cache_key = f"resolver::{type(self).__name__}::{did}"
        cache = profile.inject_or(BaseCache)
        if cache:
            async with cache.acquire(cache_key) as entry:
                if entry.result:
                    return entry.result
                else:
                    result = await self._resolve(profile, did, service_accept)
                    await entry.set_result(result, ttl=self.DEFAULT_TTL)
                    return result

        return await self._resolve(profile, did, service_accept)

    @abstractmethod
    async def _resolve(
        self,
        profile: Profile,
        did: str,
        service_accept: Optional[Sequence[Text]] = None,
    ) -> dict:
        """Resolve a DID using this resolver."""
