"""Peer DID Resolver.

Resolution is performed by converting did:peer:2 to did:peer:3 according to
https://identity.foundation/peer-did-method-spec/#generation-method:~:text=Method%203%3A%20DID%20Shortening%20with%20SHA%2D256%20Hash
"""

import logging
import re
from typing import Optional, Pattern, Sequence, Text

from did_peer_2 import PATTERN as PEER2_PATTERN, PEER3_PATTERN, peer2to3, resolve_peer3

from ...config.injection_context import InjectionContext
from ...core.event_bus import Event, EventBus
from ...core.profile import Profile
from ...storage.base import BaseStorage
from ...storage.error import StorageNotFoundError
from ...storage.record import StorageRecord
from ..base import BaseDIDResolver, DIDNotFound, ResolverType


LOGGER = logging.getLogger(__name__)


class PeerDID3Resolver(BaseDIDResolver):
    """Peer DID Resolver."""

    RECORD_TYPE_3_TO_2 = "peer3_to_peer2"

    def __init__(self):
        """Initialize Key Resolver."""
        super().__init__(ResolverType.NATIVE)

    async def setup(self, context: InjectionContext):
        """Perform required setup for Key DID resolution."""
        event_bus = context.inject(EventBus)
        event_bus.subscribe(
            re.compile("acapy::record::connections::deleted"),
            self.remove_record_for_deleted_conn,
        )

    @property
    def supported_did_regex(self) -> Pattern:
        """Return supported_did_regex of Key DID Resolver."""
        return PEER3_PATTERN

    async def _resolve(
        self,
        profile: Profile,
        did: str,
        service_accept: Optional[Sequence[Text]] = None,
    ) -> dict:
        """Resolve a did:peer:3 DID."""
        async with profile.session() as session:
            storage = session.inject(BaseStorage)
            try:
                record = await storage.get_record(self.RECORD_TYPE_3_TO_2, did)
            except StorageNotFoundError:
                raise DIDNotFound(
                    f"did:peer:3 does not correspond to a known did:peer:2 {did}"
                )

        doc = resolve_peer3(record.value)
        return doc

    async def create_and_store(self, profile: Profile, peer2: str):
        """Inject did:peer:2 create did:peer:3 and store document."""
        if not PEER2_PATTERN.match(peer2):
            raise ValueError("did:peer:2 expected")

        peer3 = peer2to3(peer2)
        async with profile.session() as session:
            storage = session.inject(BaseStorage)
            try:
                record = await storage.get_record(self.RECORD_TYPE_3_TO_2, peer3)
            except StorageNotFoundError:
                record = StorageRecord(self.RECORD_TYPE_3_TO_2, peer2, {}, peer3)
                await storage.add_record(record)
            else:
                pass

        doc = resolve_peer3(peer2)
        return doc

    async def remove_record_for_deleted_conn(self, profile: Profile, event: Event):
        """Remove record for deleted connection, if found."""
        their_did = event.payload.get("their_did")
        my_did = event.payload.get("my_did")
        if not their_did and not my_did:
            return
        dids = [
            *(did for did in (their_did, my_did) if did and PEER3_PATTERN.match(did)),
            *(
                peer2to3(did)
                for did in (their_did, my_did)
                if did and PEER2_PATTERN.match(did)
            ),
        ]
        if dids:
            LOGGER.debug(
                "Removing peer 2 to 3 mapping for deleted connection: %s", dids
            )
        async with profile.session() as session:
            storage = session.inject(BaseStorage)
            for did in dids:
                try:
                    record = StorageRecord(self.RECORD_TYPE_3_TO_2, None, None, did)
                    await storage.delete_record(record)
                except StorageNotFoundError:
                    LOGGER.debug("No peer 2 to 3 mapping found for: %s", did)
