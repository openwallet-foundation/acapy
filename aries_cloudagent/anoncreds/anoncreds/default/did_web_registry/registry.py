"""DID Web Registry"""
import re
from typing import Pattern

from .....config.injection_context import InjectionContext
from .....core.profile import Profile
from ....models.anoncreds_cred_def import (
    AnonCredsRegistryGetCredentialDefinition,
    AnonCredsRegistryGetRevocationList,
    AnonCredsRegistryGetRevocationRegistryDefinition,
)
from ....models.anoncreds_schema import AnonCredsRegistryGetSchema
from ...base_registry import BaseAnonCredsRegistrar, BaseAnonCredsResolver


class DIDWebRegistry(BaseAnonCredsResolver, BaseAnonCredsRegistrar):
    """DIDWebRegistry"""

    def __init__(self):
        self._supported_identifiers_regex = re.compile(r"^did:web:.*$")

    @property
    def supported_identifiers_regex(self) -> Pattern:
        return self._supported_identifiers_regex
        # TODO: fix regex (too general)

    async def setup(self, context: InjectionContext):
        """Setup."""
        print("Successfully registered DIDWebRegistry")

    async def get_schema(self, profile, schema_id: str) -> AnonCredsRegistryGetSchema:
        """Get a schema from the registry."""

    async def get_schemas(self, profile: Profile, filter: str):
        """Get schema ids filtered by filter"""

    # TODO: determine keyword arguments
    async def register_schema(
        self,
        profile: Profile,
        options: dict,
        schema,
    ):
        """Register a schema on the registry."""

    async def get_credential_definition(
        self, profile, credential_definition_id: str
    ) -> AnonCredsRegistryGetCredentialDefinition:
        """Get a credential definition from the registry."""

    async def get_credential_definitions(self, profile: Profile, filter: str):
        """Get credential definition ids filtered by filter"""

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

    async def get_revocation_registry_definition(
        self, revocation_registry_id: str
    ) -> AnonCredsRegistryGetRevocationRegistryDefinition:
        """Get a revocation registry definition from the registry."""

    # TODO: determine keyword arguments
    async def register_revocation_registry_definition(self):
        """Register a revocation registry definition on the registry."""

    async def get_revocation_registry_definitions(self, profile: Profile, filter: str):
        """Get credential definition ids filtered by filter"""

    async def get_revocation_list(
        self, revocation_registry_id: str, timestamp: str
    ) -> AnonCredsRegistryGetRevocationList:
        """Get a revocation list from the registry."""

    # TODO: determine keyword arguments
    async def register_revocation_list(self):
        """Register a revocation list on the registry."""
