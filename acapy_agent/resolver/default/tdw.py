"""TDW DID Resolver.

Resolution is performed by the did_tdw library.
"""

from re import Pattern
from typing import Optional, Sequence, Text

from did_tdw.resolver import ResolutionResult, resolve_did

from ...config.injection_context import InjectionContext
from ...core.profile import Profile
from ...messaging.valid import DIDTdw
from ..base import BaseDIDResolver, ResolverType


class TdwDIDResolver(BaseDIDResolver):
    """TDW DID Resolver."""

    def __init__(self):
        """Initialize the TDW DID Resolver."""
        super().__init__(ResolverType.NATIVE)

    async def setup(self, context: InjectionContext):
        """Perform required setup for TDW DID resolution."""

    @property
    def supported_did_regex(self) -> Pattern:
        """Return supported DID regex of TDW DID Resolver."""
        return DIDTdw.PATTERN

    async def _resolve(
        self, profile: Profile, did: str, service_accept: Optional[Sequence[Text]] = None
    ) -> dict:
        """Resolve DID using TDW."""
        response: ResolutionResult = await resolve_did(did)
        if response.resolution_metadata and response.resolution_metadata.get("error"):
            return response.resolution_metadata

        return response.document
