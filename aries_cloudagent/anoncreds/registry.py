"""AnonCreds Registry."""

import logging
from typing import List, Optional, Sequence

from ..core.profile import Profile
from .base import (
    AnonCredsRegistrationError,
    AnonCredsResolutionError,
    BaseAnonCredsHandler,
    BaseAnonCredsRegistrar,
    BaseAnonCredsResolver,
)
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

LOGGER = logging.getLogger(__name__)


class AnonCredsRegistry:
    """AnonCredsRegistry."""

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

    async def _resolver_for_identifier(self, identifier: str) -> BaseAnonCredsResolver:
        resolvers = [
            resolver
            for resolver in self.resolvers
            if await resolver.supports(identifier)
        ]
        if len(resolvers) == 0:
            raise AnonCredsResolutionError(
                f"No resolver available for identifier {identifier}"
            )
        if len(resolvers) > 1:
            raise AnonCredsResolutionError(
                f"More than one resolver found for identifier {identifier}"
            )
        return resolvers[0]

    async def _registrar_for_identifier(
        self, identifier: str
    ) -> BaseAnonCredsRegistrar:
        registrars = [
            registrar
            for registrar in self.registrars
            if await registrar.supports(identifier)
        ]
        if len(registrars) == 0:
            raise AnonCredsRegistrationError(
                f"No registrar available for identifier {identifier}"
            )

        if len(registrars) > 1:
            raise AnonCredsRegistrationError(
                f"More than one registrar found for identifier {identifier}"
            )
        return registrars[0]

    async def get_schema(self, profile: Profile, schema_id: str) -> GetSchemaResult:
        """Get a schema from the registry."""
        resolver = await self._resolver_for_identifier(schema_id)
        return await resolver.get_schema(profile, schema_id)

    async def register_schema(
        self,
        profile: Profile,
        schema: AnonCredsSchema,
        options: Optional[dict] = None,
    ) -> SchemaResult:
        """Register a schema on the registry."""
        registrar = await self._registrar_for_identifier(schema.issuer_id)
        return await registrar.register_schema(profile, schema, options)

    async def get_credential_definition(
        self, profile: Profile, credential_definition_id: str
    ) -> GetCredDefResult:
        """Get a credential definition from the registry."""
        resolver = await self._resolver_for_identifier(credential_definition_id)
        return await resolver.get_credential_definition(
            profile,
            credential_definition_id,
        )

    async def register_credential_definition(
        self,
        profile: Profile,
        schema: GetSchemaResult,
        credential_definition: CredDef,
        options: Optional[dict] = None,
    ) -> CredDefResult:
        """Register a credential definition on the registry."""
        registrar = await self._registrar_for_identifier(
            credential_definition.issuer_id
        )
        return await registrar.register_credential_definition(
            profile,
            schema,
            credential_definition,
            options,
        )

    async def get_revocation_registry_definition(
        self, profile: Profile, revocation_registry_id: str
    ) -> GetRevRegDefResult:
        """Get a revocation registry definition from the registry."""
        resolver = await self._resolver_for_identifier(revocation_registry_id)
        return await resolver.get_revocation_registry_definition(
            profile, revocation_registry_id
        )

    async def register_revocation_registry_definition(
        self,
        profile: Profile,
        revocation_registry_definition: RevRegDef,
        options: Optional[dict] = None,
    ) -> RevRegDefResult:
        """Register a revocation registry definition on the registry."""
        registrar = await self._registrar_for_identifier(
            revocation_registry_definition.issuer_id
        )
        return await registrar.register_revocation_registry_definition(
            profile, revocation_registry_definition, options
        )

    async def get_revocation_list(
        self, profile: Profile, rev_reg_def_id: str, timestamp: int
    ) -> GetRevListResult:
        """Get a revocation list from the registry."""
        resolver = await self._resolver_for_identifier(rev_reg_def_id)
        return await resolver.get_revocation_list(profile, rev_reg_def_id, timestamp)

    async def register_revocation_list(
        self,
        profile: Profile,
        rev_reg_def: RevRegDef,
        rev_list: RevList,
        options: Optional[dict] = None,
    ) -> RevListResult:
        """Register a revocation list on the registry."""
        registrar = await self._registrar_for_identifier(rev_list.issuer_id)
        return await registrar.register_revocation_list(
            profile, rev_reg_def, rev_list, options
        )

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
        registrar = await self._registrar_for_identifier(prev_list.issuer_id)
        return await registrar.update_revocation_list(
            profile, rev_reg_def, prev_list, curr_list, revoked, options
        )
