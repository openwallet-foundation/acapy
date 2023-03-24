"""AnonCreds Registry"""
import itertools
import logging
from typing import List, Optional, Sequence

from ...config.injection_context import InjectionContext
from ...core.profile import Profile
from ..models.anoncreds_cred_def import (
    AnonCredsRegistryGetCredentialDefinition,
    AnonCredsRegistryGetRevocationList,
    AnonCredsRegistryGetRevocationRegistryDefinition,
)
from ..models.anoncreds_schema import AnonCredsRegistryGetSchema, SchemaResult
from .base_registry import (
    AnonCredsObjectNotFound,
    AnonCredsRegistrationError,
    AnonCredsResolutionError,
    BaseAnonCredsError,
    BaseAnonCredsHandler,
    BaseAnonCredsRegistrar,
    BaseAnonCredsResolver,
)

LOGGER = logging.getLogger(__name__)


class AnonCredsRegistry:
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

    async def _resolver_for_identifier(self, identifier: str):
        resolvers = [
            resolver
            for resolver in self.resolvers
            if await resolver.supports(identifier)
        ]
        if len(resolvers) > 1:
            raise AnonCredsResolutionError(
                f"More than one resolver found for identifier {identifier}"
            )
        return resolvers[0]

    async def _registrar_for_identifier(self, identifier: str):
        registrars = [
            registrar
            for registrar in self.registrars
            if await registrar.supports(identifier)
        ]
        if len(registrars) > 1:
            raise AnonCredsRegistrationError(
                f"More than one registrar found for identifier {identifier}"
            )
        return registrars[0]

    async def setup(self, context: InjectionContext):
        """Setup method."""

    async def get_schema(
        self, profile: Profile, schema_id: str
    ) -> AnonCredsRegistryGetSchema:
        """Get a schema from the registry."""
        resolver = await self._resolver_for_identifier(schema_id)
        return await resolver.get_schema(profile, schema_id)

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
        registrar = await self._registrar_for_identifier(issuer_id)
        return await registrar.register_schema(
            profile, issuer_id, name, version, attr_names, options
        )

    async def get_credential_definition(
        self, profile: Profile, credential_definition_id: str
    ) -> AnonCredsRegistryGetCredentialDefinition:
        """Get a credential definition from the registry."""
        resolver = await self._resolver_for_identifier(credential_definition_id)
        return await resolver.get_credential_definition(
            profile,
            credential_definition_id,
        )

    async def get_credential_definitions(self, profile: Profile, filter: dict):
        """Get credential definitions id's from the registry."""
        results = [
            await resolver.get_credential_definitions(profile, filter)
            for resolver in self.resolvers
        ]
        return itertools.chain.from_iterable(results)

    # TODO: determine keyword arguments
    async def register_credential_definition(
        self,
        profile: Profile,
        schema_id: str,
        support_revocation: bool,
        tag: str,
        rev_reg_size: int,
        issuer_id: str,
    ):
        """Register a credential definition on the registry."""
        registrar = await self._registrar_for_identifier("something")
        return await registrar.register_credential_definition(
            profile,
            schema_id,
            support_revocation,
            tag,
            rev_reg_size,
            issuer_id,
        )

    async def get_revocation_registry_definition(
        self, revocation_registry_id: str
    ) -> AnonCredsRegistryGetRevocationRegistryDefinition:
        """Get a revocation registry definition from the registry."""
        resolver = await self._resolver_for_identifier(revocation_registry_id)
        return await resolver.get_revocation_registry_definition(revocation_registry_id)

    # TODO: determine keyword arguments
    async def register_revocation_registry_definition(self):
        """Register a revocation registry definition on the registry."""
        registrar = await self._registrar_for_identifier("something")
        return await registrar.register_revocation_registry_definition()

    async def get_revocation_list(
        self, revocation_registry_id: str, timestamp: str
    ) -> AnonCredsRegistryGetRevocationList:
        """Get a revocation list from the registry."""
        resolver = await self._resolver_for_identifier(revocation_registry_id)
        return await resolver.get_revocation_list(revocation_registry_id, timestamp)

    # TODO: determine keyword arguments
    async def register_revocation_list(self):
        """Register a revocation list on the registry."""
        registrar = await self._registrar_for_identifier("something")
        return await registrar.register_revocation_registry_definition()
