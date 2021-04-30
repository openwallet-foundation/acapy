"""Base Class for DID Resolvers."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Sequence, Union

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
        py_did = DID(did) if isinstance(did, str) else did

        if not self.supports(py_did.method):
            raise DIDMethodNotSupported(
                f"{self.__class__.__name__} does not support DID method {py_did.method}"
            )

        did_document = await self._resolve(profile, str(py_did))
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
        return result

    @abstractmethod
    async def _resolve(self, profile: Profile, did: str) -> dict:
        """Resolve a DID using this resolver."""
