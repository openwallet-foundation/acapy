"""WEBVH DID Resolver.

Resolution is performed by the did_webvh library.
"""

from re import Pattern
from typing import Optional, Sequence, Text

from did_webvh.resolver import ResolutionResult, resolve_did

from ...config.injection_context import InjectionContext
from ...core.profile import Profile
from ...messaging.valid import DIDWebvh
from ..base import BaseDIDResolver, ResolverType


class WebvhDIDResolver(BaseDIDResolver):
    """WEBVH DID Resolver."""

    def __init__(self):
        """Initialize the WEBVH DID Resolver."""
        super().__init__(ResolverType.NATIVE)

    async def setup(self, context: InjectionContext):
        """Perform required setup for WEBVH DID resolution."""

    @property
    def supported_did_regex(self) -> Pattern:
        """Return supported DID regex of WEBVH DID Resolver."""
        return DIDWebvh.PATTERN

    async def _resolve(
        self, profile: Profile, did: str, service_accept: Optional[Sequence[Text]] = None
    ) -> dict:
        """Resolve DID using WEBVH."""
        response: ResolutionResult = await resolve_did(did)
        if response.resolution_metadata and response.resolution_metadata.get("error"):
            return response.resolution_metadata

        return response.document
