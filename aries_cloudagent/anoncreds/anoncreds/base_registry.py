"""Base Registry"""
from abc import ABC, abstractmethod
from typing import List
from ...config.injection_context import InjectionContext

from .models import (
    AnonCredsRegistryGetCredentialDefinition,
    AnonCredsRegistryGetRevocationList,
    AnonCredsRegistryGetRevocationRegistryDefinition,
)
from ..models.anoncreds_schema import AnonCredsRegistryGetSchema


class BaseRegistry(ABC):
    """BaseRegistry"""

    def __init__(self, supported_identifiers: List[str], method_name: str):
        """Initialize Base Registry."""

    @abstractmethod
    async def setup(self, context: InjectionContext):
        """Setup method."""

    @abstractmethod
    async def get_schema(self, schema_id: str) -> AnonCredsRegistryGetSchema:
        """Get a schema from the registry."""

    # TODO: determine keyword arguments
    @abstractmethod
    async def register_schema(self):
        """Register a schema on the registry."""

    @abstractmethod
    async def get_credential_definition(
        self, credential_definition_id: str
    ) -> AnonCredsRegistryGetCredentialDefinition:
        """Get a credential definition from the registry."""

    # TODO: determine keyword arguments
    @abstractmethod
    async def register_credential_definition(self):
        """Register a credential definition on the registry."""

    @abstractmethod
    async def get_revocation_registry_definition(
        self, revocation_registry_id: str
    ) -> AnonCredsRegistryGetRevocationRegistryDefinition:
        """Get a revocation registry definition from the registry."""

    # TODO: determine keyword arguments
    @abstractmethod
    async def register_revocation_registry_definition(self):
        """Register a revocation registry definition on the registry."""

    @abstractmethod
    async def get_revocation_list(
        self, revocation_registry_id: str, timestamp: str
    ) -> AnonCredsRegistryGetRevocationList:
        """Get a revocation list from the registry."""

    # TODO: determine keyword arguments
    @abstractmethod
    async def register_revocation_list(self):
        """Register a revocation list on the registry."""
