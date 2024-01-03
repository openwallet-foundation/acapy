"""Peer DID 4 Resolver.

Resolution is performed using the peer-did-python library https://github.com/decentralized-identity/did-peer-4.
"""

from re import compile
from typing import Optional, Pattern, Sequence, Text

from did_peer_4 import (
    LONG_PATTERN,
    SHORT_PATTERN,
    long_to_short,
    resolve,
    resolve_short,
)

from ...config.injection_context import InjectionContext
from ...core.profile import Profile
from ...storage.base import BaseStorage
from ...storage.error import StorageNotFoundError
from ...storage.record import StorageRecord
from ..base import BaseDIDResolver, DIDNotFound, ResolverType


class PeerDID4Resolver(BaseDIDResolver):
    """Peer DID 4 Resolver."""

    RECORD_TYPE = "long_peer_did_4_doc"

    def __init__(self):
        """Initialize Key Resolver."""
        super().__init__(ResolverType.NATIVE)

    async def setup(self, context: InjectionContext):
        """Perform required setup for Key DID resolution."""

    @property
    def supported_did_regex(self) -> Pattern:
        """Return supported_did_regex of Key DID Resolver."""
        # accepts both, return a Regex OR
        return compile(f"{LONG_PATTERN.pattern}|{SHORT_PATTERN.pattern}")

    async def _resolve(
        self,
        profile: Profile,
        did: str,
        service_accept: Optional[Sequence[Text]] = None,
    ) -> dict:
        """Resolve a Key DID."""
        if LONG_PATTERN.match(did):
            short_did_peer_4 = long_to_short(did)
            # resolve and save long form
            async with profile.session() as session:
                storage = session.inject(BaseStorage)
                try:
                    record = await storage.get_record(
                        self.RECORD_TYPE, short_did_peer_4
                    )
                except StorageNotFoundError:
                    record = StorageRecord(self.RECORD_TYPE, did, {}, short_did_peer_4)
                    await storage.add_record(record)
            document = resolve(did)

        elif SHORT_PATTERN.match(did):
            async with profile.session() as session:
                storage = session.inject(BaseStorage)
                try:
                    record = await storage.get_record(self.RECORD_TYPE, did)
                except StorageNotFoundError:
                    raise DIDNotFound(
                        f"short did:peer:4 does not correspond to a \
                          known long did:peer:4 {did}"
                    )
            document = resolve_short(record.value)
        else:
            raise ValueError(f"{did} did not match long or short form of did:peer:4")

        return document
