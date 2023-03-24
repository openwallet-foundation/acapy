"""Base Registry"""
from abc import ABC, abstractmethod
from typing import Generic, Optional, Pattern, Sequence, Tuple, TypeVar

from aries_cloudagent.core.error import BaseError

from ...config.injection_context import InjectionContext
from ...core.profile import Profile
from ..models.anoncreds_cred_def import (
    AnonCredsRegistryGetCredentialDefinition,
    AnonCredsRegistryGetCredentialDefinitions,
    AnonCredsRegistryGetRevocationList,
    AnonCredsRegistryGetRevocationRegistryDefinition,
    AnonCredsRegistryGetRevocationRegistryDefinitions,
)
from ..models.anoncreds_schema import (
    AnonCredsRegistryGetSchema,
    AnonCredsRegistryGetSchemas,
    SchemaResult,
)


T = TypeVar("T")


class BaseAnonCredsError(BaseError):
    """Base error class for AnonCreds."""


class AnonCredsObjectNotFound(BaseAnonCredsError):
    """Raised when object is not found in resolver."""


class AnonCredsRegistrationError(BaseAnonCredsError):
    """Raised when registering an AnonCreds object fails."""


class AnonCredsObjectAlreadyExists(AnonCredsRegistrationError, Generic[T]):
    """Raised when an AnonCreds object already exists."""

    def __init__(
        self, message: Optional[str] = None, obj: Optional[T] = None, *args, **kwargs
    ):
        super().__init__(message, obj, *args, **kwargs)
        self.obj = obj

    @property
    def message(self):
        if self.args[0] and self.args[1]:
            return f"{self.args[0]}: {self.args[1]}"
        else:
            return super().message


class AnonCredsSchemaAlreadyExists(AnonCredsObjectAlreadyExists[Tuple[str, dict]]):
    """Raised when a schema already exists."""

    @property
    def schema_id(self):
        return self.obj[0]

    @property
    def schema(self):
        return self.obj[1]


class AnonCredsResolutionError(BaseAnonCredsError):
    """Raised when resolving an AnonCreds object fails."""


class BaseAnonCredsHandler(ABC):
    @property
    @abstractmethod
    def supported_identifiers_regex(self) -> Pattern:
        """Regex to match supported identifiers."""

    async def supports(self, identifier: str) -> bool:
        """Determine whether this registry supports the given identifier."""
        return bool(self.supported_identifiers_regex.match(identifier))

    @abstractmethod
    async def setup(self, context: InjectionContext):
        """Setup method."""


class BaseAnonCredsResolver(BaseAnonCredsHandler):
    @abstractmethod
    async def get_schema(self, schema_id: str) -> AnonCredsRegistryGetSchema:
        """Get a schema from the registry."""

    @abstractmethod
    async def get_schemas(
        self, profile: Profile, filter: dict
    ) -> AnonCredsRegistryGetSchemas:
        """Get a schema ids from the registry."""

    @abstractmethod
    async def get_credential_definition(
        self, credential_definition_id: str
    ) -> AnonCredsRegistryGetCredentialDefinition:
        """Get a credential definition from the registry."""

    @abstractmethod
    async def get_credential_definitions(
        self, profile: Profile, filter: dict
    ) -> AnonCredsRegistryGetCredentialDefinitions:
        """Get a credential definition ids from the registry."""

    @abstractmethod
    async def get_revocation_registry_definition(
        self, revocation_registry_id: str
    ) -> AnonCredsRegistryGetRevocationRegistryDefinition:
        """Get a revocation registry definition from the registry."""

    @abstractmethod
    async def get_revocation_registry_definitions(
        self, filter: dict
    ) -> AnonCredsRegistryGetRevocationRegistryDefinitions:
        """Get a revocation registry definition ids from the registry."""

    @abstractmethod
    async def get_revocation_list(
        self, revocation_registry_id: str, timestamp: str
    ) -> AnonCredsRegistryGetRevocationList:
        """Get a revocation list from the registry."""


class BaseAnonCredsRegistrar(BaseAnonCredsHandler):
    @abstractmethod
    async def register_schema(
        self,
        profile: Profile,
        issuer_id: str,
        name: str,
        version: str,
        attr_names: Sequence[str],
        options: Optional[dict] = None,
    ) -> SchemaResult:
        """Register a schema on the registry."""

    # TODO: determine keyword arguments
    @abstractmethod
    async def register_credential_definition(self):
        """Register a credential definition on the registry."""

    # TODO: determine keyword arguments
    @abstractmethod
    async def register_revocation_registry_definition(self):
        """Register a revocation registry definition on the registry."""

    # TODO: determine keyword arguments
    @abstractmethod
    async def register_revocation_list(self):
        """Register a revocation list on the registry."""
