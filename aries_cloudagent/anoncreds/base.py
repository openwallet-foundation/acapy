"""Base Registry"""
from abc import ABC, abstractmethod
from typing import Generic, Optional, Pattern, Tuple, TypeVar

from ..config.injection_context import InjectionContext
from ..core.error import BaseError
from ..core.profile import Profile
from .models.anoncreds_cred_def import (
    CredDef,
    CredDefResult,
    GetCredDefResult,
)
from .models.anoncreds_revocation import (
    GetRevStatusListResult,
    AnonCredsRegistryGetRevocationRegistryDefinition,
    RevRegDef,
    RevRegDefResult,
    RevStatusList,
    RevStatusListResult,
)
from .models.anoncreds_schema import AnonCredsSchema, GetSchemaResult, SchemaResult


T = TypeVar("T")


class BaseAnonCredsError(BaseError):
    """Base error class for AnonCreds."""


class AnonCredsObjectNotFound(BaseAnonCredsError):
    """Raised when object is not found in resolver."""

    def __init__(
        self, message: Optional[str] = None, resolution_metadata: Optional[dict] = None
    ):
        super().__init__(message, resolution_metadata)
        self.resolution_metadata = resolution_metadata


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


class AnonCredsSchemaAlreadyExists(
    AnonCredsObjectAlreadyExists[Tuple[str, AnonCredsSchema]]
):
    """Raised when a schema already exists."""

    @property
    def schema_id(self):
        return self.obj[0] if self.obj else None

    @property
    def schema(self):
        return self.obj[1] if self.obj else None


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
    async def get_schema(self, profile: Profile, schema_id: str) -> GetSchemaResult:
        """Get a schema from the registry."""

    @abstractmethod
    async def get_credential_definition(
        self, profile: Profile, credential_definition_id: str
    ) -> GetCredDefResult:
        """Get a credential definition from the registry."""

    @abstractmethod
    async def get_revocation_registry_definition(
        self, profile: Profile, revocation_registry_id: str
    ) -> AnonCredsRegistryGetRevocationRegistryDefinition:
        """Get a revocation registry definition from the registry."""

    @abstractmethod
    async def get_revocation_status_list(
        self, profile: Profile, revocation_registry_id: str, timestamp: str
    ) -> GetRevStatusListResult:
        """Get a revocation list from the registry."""


class BaseAnonCredsRegistrar(BaseAnonCredsHandler):
    @abstractmethod
    async def register_schema(
        self,
        profile: Profile,
        schema: AnonCredsSchema,
        options: Optional[dict] = None,
    ) -> SchemaResult:
        """Register a schema on the registry."""

    @abstractmethod
    async def register_credential_definition(
        self,
        profile: Profile,
        schema: GetSchemaResult,
        credential_definition: CredDef,
        options: Optional[dict] = None,
    ) -> CredDefResult:
        """Register a credential definition on the registry."""

    @abstractmethod
    async def register_revocation_registry_definition(
        self,
        profile: Profile,
        revocation_registry_definition: RevRegDef,
        options: Optional[dict] = None,
    ) -> RevRegDefResult:
        """Register a revocation registry definition on the registry."""

    @abstractmethod
    async def register_revocation_status_list(
        self,
        profile: Profile,
        rev_status_list: RevStatusList,
        options: Optional[dict] = None,
    ) -> RevStatusListResult:
        """Register a revocation list on the registry."""
