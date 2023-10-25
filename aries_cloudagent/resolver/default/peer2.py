"""Peer DID Resolver.

Resolution is performed using the peer-did-python library https://github.com/sicpa-dlab/peer-did-python.
"""

from typing import Optional, Pattern, Sequence, Text

from did_peer_2 import resolve, PATTERN

from ...config.injection_context import InjectionContext
from ...core.profile import Profile
from ..base import BaseDIDResolver, DIDNotFound, ResolverType
from .peer3 import PeerDID3Resolver


class PeerDID2Resolver(BaseDIDResolver):
    """Peer DID Resolver."""

    def __init__(self):
        """Initialize Key Resolver."""
        super().__init__(ResolverType.NATIVE)

    async def setup(self, context: InjectionContext):
        """Perform required setup for Key DID resolution."""

    @property
    def supported_did_regex(self) -> Pattern:
        """Return supported_did_regex of Key DID Resolver."""
        return PATTERN

    async def _resolve(
        self,
        profile: Profile,
        did: str,
        service_accept: Optional[Sequence[Text]] = None,
    ) -> dict:
        """Resolve a Key DID."""
        if not PATTERN.match(did):
            raise DIDNotFound(f"did is not a peer did: {did}")

        doc = resolve(did)
        await PeerDID3Resolver().create_and_store(profile, did)

        return doc
