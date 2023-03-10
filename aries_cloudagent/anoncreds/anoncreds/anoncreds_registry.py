"""AnonCreds Registry"""
import logging
from typing import List

from .base_registry import BaseRegistry
from .models import (
    AnonCredsRegistryGetCredentialDefinition,
    AnonCredsRegistryGetRevocationList,
    AnonCredsRegistryGetRevocationRegistryDefinition,
    AnonCredsRegistryGetSchema,
)
from ...config.injection_context import InjectionContext


LOGGER = logging.getLogger(__name__)


class AnonCredsRegistry(BaseRegistry):
    """AnonCredsRegistry"""

    def __init__(self, registries: List[BaseRegistry] = None):
        """Create DID Resolver."""
        super().__init__(supported_identifiers=[], method_name="")
        # TODO: need both supported_identifiers and method_name?
        self.registries = registries or []

    # TODO: use supported_identifier and method_name to select which registry should
    # resolve or register a given object + identifier

    def register_registry(self, registry: BaseRegistry):
        """Register a new registry."""
        self.registries.append(registry)

    async def setup(self, context: InjectionContext):
        """Setup method."""

    async def get_schema(self, schema_id: str) -> AnonCredsRegistryGetSchema:
        """Get a schema from the registry."""

    # TODO: determine keyword arguments
    async def register_schema(self):
        """Register a schema on the registry."""

    async def get_credential_definition(
        self, credential_definition_id: str
    ) -> AnonCredsRegistryGetCredentialDefinition:
        """Get a credential definition from the registry."""

    # TODO: determine keyword arguments
    async def register_credential_definition(self):
        """Register a credential definition on the registry."""

    async def get_revocation_registry_definition(
        self, revocation_registry_id: str
    ) -> AnonCredsRegistryGetRevocationRegistryDefinition:
        """Get a revocation registry definition from the registry."""

    # TODO: determine keyword arguments
    async def register_revocation_registry_definition(self):
        """Register a revocation registry definition on the registry."""

    async def get_revocation_list(
        self, revocation_registry_id: str, timestamp: str
    ) -> AnonCredsRegistryGetRevocationList:
        """Get a revocation list from the registry."""

    # TODO: determine keyword arguments
    async def register_revocation_list(self):
        """Register a revocation list on the registry."""
