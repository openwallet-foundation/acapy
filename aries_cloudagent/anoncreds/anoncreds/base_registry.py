"""Base Registry"""
from abc import ABC, abstractmethod
from typing import Pattern

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
)


class BaseAnonCredsError(Exception):
    """Base error class for AnonCreds."""


class AnonCredsObjectNotFound(BaseAnonCredsError):
    """Raised when object is not found in resolver."""


class AnonCredsRegistrationFailed(BaseAnonCredsError):
    """Raised when registering an AnonCreds object fails."""


class AnonCredsResolutionFailed(BaseAnonCredsError):
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

    # TODO: determine keyword arguments
    @abstractmethod
    async def register_schema(self):
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
