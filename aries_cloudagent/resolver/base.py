"""Base Class for DID Resolvers."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Sequence, Union
from datetime import datetime

from pydid import DID, DIDDocument
from pydid.options import (
    doc_allow_public_key,
    doc_insert_missing_ids,
    vm_allow_controller_list,
    vm_allow_missing_controller,
    vm_allow_type_list,
)

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


class ResolutionResult:
    """Resolution Class to pack the DID Doc and the resolution information."""

    def __init__(self, did_doc: DIDDocument, resolver_metadata: dict):
        """Initialize Resolution.

        Args:
            did_doc: DID Document resolved
            resolver_metadata: Resolving details
        """
        self.did_doc = did_doc
        self.resolver_metadata = resolver_metadata


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

    async def resolve(self, profile: Profile, did: Union[str, DID]) -> ResolutionResult:
        """Resolve a DID using this resolver."""
        py_did = DID(did) if isinstance(did, str) else did

        if not self.supports(py_did.method):
            raise DIDMethodNotSupported(
                f"{self.__class__.__name__} does not support DID method {py_did.method}"
            )
        resolution_start_time = datetime.utcnow()
        did_document = await self._resolve(profile, str(py_did))
        resolver_metadata = await self._retrieve_resolver_metadata(
            py_did.method, resolution_start_time
        )
        result = DIDDocument.deserialize(
            did_document,
            options={
                doc_insert_missing_ids,
                doc_allow_public_key,
                vm_allow_controller_list,
                vm_allow_missing_controller,
                vm_allow_type_list,
            },
        )
        return ResolutionResult(result, resolver_metadata)

    @abstractmethod
    async def _resolve(self, profile: Profile, did: str) -> dict:
        """Resolve a DID using this resolver."""

    async def _retrieve_resolver_metadata(self, method, resolution_start_time):

        time_now = datetime.utcnow()
        duration = int((time_now - resolution_start_time).total_seconds() * 1000)
        internal_class = self.__class__
        module = internal_class.__module__
        class_name = internal_class.__qualname__

        resolver_metadata = {
            "type": self.type.value,
            "driverId": f"did:{method}",
            "resolver": module + "." + class_name,
            "retrieved": time_now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "duration": duration,
        }

        return resolver_metadata
