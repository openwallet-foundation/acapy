"""DID Indy Registry"""
import logging
import re
from typing import Pattern

from .....config.injection_context import InjectionContext
from .....core.profile import Profile
from ....models.anoncreds_cred_def import (
    GetCredDefResult,
)
from ....models.anoncreds_revocation import (
    AnonCredsRegistryGetRevocationList,
    AnonCredsRegistryGetRevocationRegistryDefinition,
)
from ....models.anoncreds_schema import GetSchemaResult
from ...base_registry import BaseAnonCredsRegistrar, BaseAnonCredsResolver

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

    async def get_schema(self, profile: Profile, schema_id) -> GetSchemaResult:
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
        self, profile: Profile, cred_def_id: str
    ) -> GetCredDefResult:
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
        self, profile: Profile, rev_reg_id: str
    ) -> AnonCredsRegistryGetRevocationRegistryDefinition:
        """Get a revocation registry definition from the registry."""

    # TODO: determine keyword arguments
    async def register_revocation_registry_definition(
        self,
        profile: Profile,
        rev_reg_id: str,
        issuer_id: str,
    ):
        """Register a revocation registry definition on the registry."""

    async def get_revocation_registry_definitions(self, profile: Profile, filter: str):
        """Get credential definition ids filtered by filter"""

    async def get_revocation_list(
        self, revocation_registry_id: str, timestamp: str
    ) -> AnonCredsRegistryGetRevocationList:
        """Get a revocation list from the registry."""

    # TODO: determine keyword arguments
    async def register_revocation_status_list(self):
        """Register a revocation list on the registry."""
