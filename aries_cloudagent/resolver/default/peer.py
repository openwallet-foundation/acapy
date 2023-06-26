"""Key DID Resolver.

Resolution is performed using the IndyLedger class.
"""

from typing import Optional, Pattern, Sequence, Text
from peerdid.dids import is_peer_did, PEER_DID_PATTERN, resolve_peer_did

from ...config.injection_context import InjectionContext
from ...core.profile import Profile
from ...messaging.valid import DIDKey as DIDKeyType

from ..base import BaseDIDResolver, DIDNotFound, ResolverType


class PeerDIDResolver(BaseDIDResolver):
    """Peer DID Resolver."""

    def __init__(self):
        """Initialize Key Resolver."""
        super().__init__(ResolverType.NATIVE)

    async def setup(self, context: InjectionContext):
        """Perform required setup for Key DID resolution."""

    @property
    def supported_did_regex(self) -> Pattern:
        """Return supported_did_regex of Key DID Resolver."""
        return PEER_DID_PATTERN

    async def _resolve(
        self,
        profile: Profile,
        did: str,
        service_accept: Optional[Sequence[Text]] = None,
    ) -> dict:
        """Resolve a Key DID."""
        try:
            peer_did = is_peer_did(did)
        except Exception as e:
            raise DIDNotFound(f"peer_did is not formatted correctly: {did}") from e

        did_doc = resolve_peer_did(peer_did)

        return did_doc.dict()
