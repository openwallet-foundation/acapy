"""Indy DID Resolver.

Resolution is performed using the IndyLedger class.
"""
from typing import Sequence

from ...did.did_key import DIDKey
from ...config.injection_context import InjectionContext
from ...core.profile import Profile
from ..base import BaseDIDResolver, DIDNotFound, ResolverType


class KeyDIDResolver(BaseDIDResolver):
    """Key DID Resolver."""

    def __init__(self):
        """Initialize Key Resolver."""
        super().__init__(ResolverType.NATIVE)

    async def setup(self, context: InjectionContext):
        """Perform required setup for Key DID resolution."""

    @property
    def supported_methods(self) -> Sequence[str]:
        """Return supported methods of Key DID Resolver."""
        return ["key"]

    async def _resolve(self, profile: Profile, did: str) -> dict:
        """Resolve a Key DID."""
        try:
            did_key = DIDKey.from_did(did)

        except Exception as e:
            raise DIDNotFound(f"Unable to resolve did: {did}") from e

        return did_key.did_doc
