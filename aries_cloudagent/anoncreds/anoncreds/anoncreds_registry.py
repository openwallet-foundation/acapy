"""AnonCreds Registry"""
import logging
from typing import List, Optional

from ...config.injection_context import InjectionContext
from .base_registry import (
    AnonCredsObjectNotFound,
    AnonCredsRegistrationFailed,
    BaseAnonCredsError,
    BaseAnonCredsHandler,
    BaseAnonCredsRegistrar,
    BaseAnonCredsResolver,
)
from .models import (
    AnonCredsRegistryGetCredentialDefinition,
    AnonCredsRegistryGetRevocationList,
    AnonCredsRegistryGetRevocationRegistryDefinition,
    AnonCredsRegistryGetSchema,
)


LOGGER = logging.getLogger(__name__)


class AnonCredsRegistry(BaseAnonCredsResolver, BaseAnonCredsRegistrar):
    """AnonCredsRegistry"""

    def __init__(self, registries: Optional[List[BaseAnonCredsHandler]] = None):
        """Create DID Resolver."""
        self.resolvers = []
        self.registrars = []
        if registries:
            for registry in registries:
                self.register(registry)

    def register(self, registry: BaseAnonCredsHandler):
        """Register a new registry."""
        if isinstance(registry, BaseAnonCredsResolver):
            self.resolvers.append(registry)
        if isinstance(registry, BaseAnonCredsRegistrar):
            self.registrars.append(registry)

    async def _resolvers_for_identifier(self, identifier: str):
        return [
            resolver
            for resolver in self.resolvers
            if await resolver.supports(identifier)
        ]

    async def _registrars_for_identifiers(self, identifier: str):
        return [
            registrar
            for registrar in self.registrars
            if await registrar.supports(identifier)
        ]

    async def setup(self, context: InjectionContext):
        """Setup method."""

    async def get_schema(self, schema_id: str) -> AnonCredsRegistryGetSchema:
        """Get a schema from the registry."""
        for resolver in await self._resolvers_for_identifier(schema_id):
            try:
                return await resolver.get_schema(schema_id)
            except BaseAnonCredsError:
                LOGGER.exception("Error getting schema from resolver")

        raise AnonCredsObjectNotFound(f"{schema_id} could not be resolved")

    # TODO: determine keyword arguments
    async def register_schema(self):
        """Register a schema on the registry."""
        for registrar in await self._registrars_for_identifiers("something"):
            try:
                return await registrar.register_schema()
            except BaseAnonCredsError:
                LOGGER.exception("Error registering schema with registrar")

        raise AnonCredsRegistrationFailed("Failed to register schema")

    async def get_credential_definition(
        self, credential_definition_id: str
    ) -> AnonCredsRegistryGetCredentialDefinition:
        """Get a credential definition from the registry."""
        for resolver in await self._resolvers_for_identifier(credential_definition_id):
            try:
                return await resolver.get_credential_definition(
                    credential_definition_id
                )
            except BaseAnonCredsError:
                LOGGER.exception("Error getting credential definition from resolver")

        raise AnonCredsObjectNotFound(
            f"{credential_definition_id} could not be resolved"
        )

    # TODO: determine keyword arguments
    async def register_credential_definition(self):
        """Register a credential definition on the registry."""
        for registrar in await self._registrars_for_identifiers("something"):
            try:
                return await registrar.register_credential_definition()
            except BaseAnonCredsError:
                LOGGER.exception("Error registering schema with registrar")

        raise AnonCredsRegistrationFailed("Failed to register credential definition")

    async def get_revocation_registry_definition(
        self, revocation_registry_id: str
    ) -> AnonCredsRegistryGetRevocationRegistryDefinition:
        """Get a revocation registry definition from the registry."""
        for resolver in await self._resolvers_for_identifier(revocation_registry_id):
            try:
                return await resolver.get_revocation_registry_definition(
                    revocation_registry_id
                )
            except BaseAnonCredsError:
                LOGGER.exception(
                    "Error getting revocation registry definition from resolver"
                )

        raise AnonCredsObjectNotFound(f"{revocation_registry_id} could not be resolved")

    # TODO: determine keyword arguments
    async def register_revocation_registry_definition(self):
        """Register a revocation registry definition on the registry."""
        for registrar in await self._registrars_for_identifiers("something"):
            try:
                return await registrar.register_revocation_registry_definition()
            except BaseAnonCredsError:
                LOGGER.exception("Error registering schema with registrar")

        raise AnonCredsRegistrationFailed(
            "Failed to register revocation registry definition"
        )

    async def get_revocation_list(
        self, revocation_registry_id: str, timestamp: str
    ) -> AnonCredsRegistryGetRevocationList:
        """Get a revocation list from the registry."""
        for resolver in await self._resolvers_for_identifier(revocation_registry_id):
            try:
                return await resolver.get_revocation_list(
                    revocation_registry_id, timestamp
                )
            except BaseAnonCredsError:
                LOGGER.exception("Error getting revocation list from resolver")

        raise AnonCredsObjectNotFound(f"{revocation_registry_id} could not be resolved")

    # TODO: determine keyword arguments
    async def register_revocation_list(self):
        """Register a revocation list on the registry."""
        for registrar in await self._registrars_for_identifiers("something"):
            try:
                return await registrar.register_revocation_registry_definition()
            except BaseAnonCredsError:
                LOGGER.exception("Error registering schema with registrar")

        raise AnonCredsRegistrationFailed("Failed to register revocation list")
