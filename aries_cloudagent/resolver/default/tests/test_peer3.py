"""Test PeerDIDResolver."""

import pytest
from aries_cloudagent.connections.models.conn_record import ConnRecord

from aries_cloudagent.core.event_bus import EventBus

from .. import peer3 as test_module
from ....core.in_memory import InMemoryProfile
from ....core.profile import Profile
from ..peer2 import PeerDID2Resolver
from ..peer3 import PeerDID3Resolver
from did_peer_2 import peer2to3


TEST_DP2 = "did:peer:2.Ez6LSpkcni2KTTxf4nAp6cPxjRbu26Tj4b957BgHcknVeNFEj.Vz6MksXhfmxm2i3RnoHH2mKQcx7EY4tToJR9JziUs6bp8a6FM.SeyJ0IjoiZGlkLWNvbW11bmljYXRpb24iLCJzIjoiaHR0cDovL2hvc3QuZG9ja2VyLmludGVybmFsOjkwNzAiLCJyZWNpcGllbnRfa2V5cyI6W119"

TEST_DP3 = peer2to3(TEST_DP2)


@pytest.fixture
def event_bus():
    yield EventBus()


@pytest.fixture
def profile(event_bus: EventBus):
    """Profile fixture."""
    profile = InMemoryProfile.test_profile()
    profile.context.injector.bind_instance(EventBus, event_bus)
    yield profile


@pytest.fixture
async def resolver(profile):
    """Resolver fixture."""
    instance = PeerDID3Resolver()
    await instance.setup(profile.context)
    yield instance


@pytest.fixture
def peer2_resolver():
    """Resolver fixture."""
    yield PeerDID2Resolver()


@pytest.mark.asyncio
async def test_resolve_2_then_3(
    profile: Profile, resolver: PeerDID3Resolver, peer2_resolver: PeerDID2Resolver
):
    """Test resolver setup."""
    assert resolver.supported_did_regex
    assert await resolver.supports(profile, TEST_DP3)

    await peer2_resolver.resolve(profile, TEST_DP2)
    doc = await resolver.resolve(profile, TEST_DP3)

    assert doc
    assert doc["id"] == TEST_DP3
    assert "service" in doc
    assert "verificationMethod" in doc
    assert len(doc["verificationMethod"]) == 2


@pytest.mark.asyncio
async def test_resolve_x_no_2(profile: Profile, resolver: PeerDID3Resolver):
    """Test resolver setup."""
    with pytest.raises(test_module.DIDNotFound):
        await resolver.resolve(profile, TEST_DP3)


@pytest.mark.asyncio
async def test_record_removal(
    profile: Profile,
    resolver: PeerDID3Resolver,
    peer2_resolver: PeerDID2Resolver,
):
    """Test resolver setup."""
    await peer2_resolver.resolve(profile, TEST_DP2)
    assert await resolver.resolve(profile, TEST_DP3)
    record = ConnRecord(
        connection_id="test",
        my_did=TEST_DP2,
        their_did=TEST_DP3,
    )
    record.state = ConnRecord.STATE_DELETED
    async with profile.session() as session:
        await record.emit_event(session, record.serialize())

    with pytest.raises(test_module.DIDNotFound):
        doc = await resolver.resolve(profile, TEST_DP3)
