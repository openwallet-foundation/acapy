"""Test PeerDIDResolver."""

import pytest

from ....core.in_memory import InMemoryProfile
from ....core.profile import Profile
from ..peer2 import PeerDID2Resolver


TEST_DID0 = "did:peer:2.Ez6LSpkcni2KTTxf4nAp6cPxjRbu26Tj4b957BgHcknVeNFEj.Vz6MksXhfmxm2i3RnoHH2mKQcx7EY4tToJR9JziUs6bp8a6FM.SeyJ0IjoiZGlkLWNvbW11bmljYXRpb24iLCJzIjoiaHR0cDovL2hvc3QuZG9ja2VyLmludGVybmFsOjkwNzAiLCJyZWNpcGllbnRfa2V5cyI6W119"


@pytest.fixture
def resolver():
    """Resolver fixture."""
    yield PeerDID2Resolver()


@pytest.fixture
def profile():
    """Profile fixture."""
    profile = InMemoryProfile.test_profile()
    yield profile


@pytest.mark.asyncio
async def test_resolver(profile: Profile, resolver: PeerDID2Resolver):
    """Test resolver setup."""
    assert resolver.supported_did_regex
    assert await resolver.supports(profile, TEST_DID0)
    doc = await resolver.resolve(profile, TEST_DID0)
    assert doc
    assert doc["id"] == TEST_DID0
    assert "service" in doc
    assert "verificationMethod" in doc
    assert len(doc["verificationMethod"]) == 2
