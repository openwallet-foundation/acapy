"""Base Registry."""

from abc import ABC, abstractmethod
from typing import Generic, Optional, Pattern, Sequence, TypeVar

from ..config.injection_context import InjectionContext
from ..core.error import BaseError
from ..core.profile import Profile
from .models.anoncreds_cred_def import (
    CredDef,
    CredDefResult,
    GetCredDefResult,
)
from .models.anoncreds_revocation import (
    GetRevListResult,
    GetRevRegDefResult,
    RevList,
    RevListResult,
    RevRegDef,
    RevRegDefResult,
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
        """Constructor."""
        super().__init__(message, resolution_metadata)
        self.resolution_metadata = resolution_metadata or {}


class AnonCredsRegistrationError(BaseAnonCredsError):
    """Raised when registering an AnonCreds object fails."""


class AnonCredsObjectAlreadyExists(AnonCredsRegistrationError, Generic[T]):
    """Raised when an AnonCreds object already exists."""

    def __init__(
        self,
        message: str,
        obj_id: str,
        obj: T = None,
        *args,
        **kwargs,
    ):
        """Initialize an instance.

        Args:
            message: Message
            obj_id: Object ID
            obj: Object

        TODO: update this docstring - Anoncreds-break.

        """
        super().__init__(message, obj_id, obj, *args, **kwargs)
        self._message = message
        self.obj_id = obj_id
        self.obj = obj

    @property
    def message(self):
        """Message."""
        return f"{self._message}: {self.obj_id}, {self.obj}"


class AnonCredsSchemaAlreadyExists(AnonCredsObjectAlreadyExists[AnonCredsSchema]):
    """Raised when a schema already exists."""

    @property
    def schema_id(self):
        """Get Schema Id."""
        return self.obj_id

    @property
    def schema(self):
        """Get Schema."""
        return self.obj


class AnonCredsResolutionError(BaseAnonCredsError):
    """Raised when resolving an AnonCreds object fails."""


class BaseAnonCredsHandler(ABC):
    """Base Anon Creds Handler."""

    @property
    @abstractmethod
    def supported_identifiers_regex(self) -> Pattern:
        """Regex to match supported identifiers."""

    async def supports(self, identifier: str) -> bool:
        """Determine whether this registry supports the given identifier."""
        return bool(self.supported_identifiers_regex.match(identifier))

    @abstractmethod
    async def setup(self, context: InjectionContext):
        """Class Setup method."""


class BaseAnonCredsResolver(BaseAnonCredsHandler):
    """Base Anon Creds Resolver."""

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
    ) -> GetRevRegDefResult:
        """Get a revocation registry definition from the registry."""

    @abstractmethod
    async def get_revocation_list(
        self, profile: Profile, revocation_registry_id: str, timestamp: int
    ) -> GetRevListResult:
        """Get a revocation list from the registry."""


class BaseAnonCredsRegistrar(BaseAnonCredsHandler):
    """Base Anon Creds Registrar."""

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
    async def register_revocation_list(
        self,
        profile: Profile,
        rev_reg_def: RevRegDef,
        rev_list: RevList,
        options: Optional[dict] = None,
    ) -> RevListResult:
        """Register a revocation list on the registry."""

    @abstractmethod
    async def update_revocation_list(
        self,
        profile: Profile,
        rev_reg_def: RevRegDef,
        prev_list: RevList,
        curr_list: RevList,
        revoked: Sequence[int],
        options: Optional[dict] = None,
    ) -> RevListResult:
        """Update a revocation list on the registry."""
