"""DID Indy Registry"""
import logging
import re
from typing import Optional, Pattern

from ....config.injection_context import InjectionContext
from ....core.profile import Profile
from ...models.anoncreds_cred_def import (
    CredDef,
    CredDefResult,
    GetCredDefResult,
)
from ...models.anoncreds_revocation import (
    GetRevStatusListResult,
    AnonCredsRegistryGetRevocationRegistryDefinition,
    RevRegDef,
    RevRegDefResult,
    RevStatusList,
    RevStatusListResult,
)
from ...models.anoncreds_schema import AnonCredsSchema, GetSchemaResult, SchemaResult
from ...base import BaseAnonCredsRegistrar, BaseAnonCredsResolver

LOGGER = logging.getLogger(__name__)


class DIDIndyRegistry(BaseAnonCredsResolver, BaseAnonCredsRegistrar):
    """DIDIndyRegistry"""

    def __init__(self):
        self._supported_identifiers_regex = re.compile(r"^did:indy:.*$")

    @property
    def supported_identifiers_regex(self) -> Pattern:
        return self._supported_identifiers_regex
        # TODO: fix regex (too general)

    async def setup(self, context: InjectionContext):
        """Setup."""
        print("Successfully registered DIDIndyRegistry")

    async def get_schema(self, profile: Profile, schema_id: str) -> GetSchemaResult:
        """Get a schema from the registry."""
        raise NotImplementedError()

    async def register_schema(
        self,
        profile: Profile,
        schema: AnonCredsSchema,
        options: Optional[dict],
    ) -> SchemaResult:
        """Register a schema on the registry."""
        raise NotImplementedError()

    async def get_credential_definition(
        self, profile: Profile, credential_definition_id: str
    ) -> GetCredDefResult:
        """Get a credential definition from the registry."""
        raise NotImplementedError()

    async def register_credential_definition(
        self,
        profile: Profile,
        schema: GetSchemaResult,
        credential_definition: CredDef,
        options: Optional[dict] = None,
    ) -> CredDefResult:
        """Register a credential definition on the registry."""
        raise NotImplementedError()

    async def get_revocation_registry_definition(
        self, profile: Profile, revocation_registry_id: str
    ) -> AnonCredsRegistryGetRevocationRegistryDefinition:
        """Get a revocation registry definition from the registry."""
        raise NotImplementedError()

    async def register_revocation_registry_definition(
        self,
        profile: Profile,
        revocation_registry_definition: RevRegDef,
        options: Optional[dict] = None,
    ) -> RevRegDefResult:
        """Register a revocation registry definition on the registry."""
        raise NotImplementedError()

    async def get_revocation_status_list(
        self, profile: Profile, revocation_registry_id: str, timestamp: int
    ) -> GetRevStatusListResult:
        """Get a revocation list from the registry."""
        raise NotImplementedError()

    async def register_revocation_status_list(
        self,
        profile: Profile,
        rev_reg_def: RevRegDef,
        rev_status_list: RevStatusList,
        options: Optional[dict] = None,
    ) -> RevStatusListResult:
        """Register a revocation list on the registry."""
        raise NotImplementedError()

    async def update_revocation_status_list(
        self,
        profile: Profile,
        rev_reg_def: RevRegDef,
        prev_status_list: RevStatusList,
        curr_status_list: RevStatusList,
        options: Optional[dict] = None,
    ) -> RevStatusListResult:
        """Update a revocation list on the registry."""
        raise NotImplementedError()
