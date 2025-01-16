import pytest

from ....core.profile import Profile
from ....messaging.valid import DIDWebvh
from ....utils.testing import create_test_profile
from ..webvh import WebvhDIDResolver

TEST_DID = "did:webvh:Qma6mc1qZw3NqxwX6SB5GPQYzP4pGN2nXD15Jwi4bcDBKu:domain.example"


@pytest.fixture
def resolver():
    """Resolver fixture."""
    yield WebvhDIDResolver()


@pytest.fixture
async def profile():
    """Profile fixture."""
    yield await create_test_profile()


@pytest.mark.asyncio
async def test_supported_did_regex(profile, resolver: WebvhDIDResolver):
    """Test the supported_did_regex."""
    assert resolver.supported_did_regex == DIDWebvh.PATTERN
    assert await resolver.supports(
        profile,
        TEST_DID,
    )


@pytest.mark.asyncio
async def test_resolve(resolver: WebvhDIDResolver, profile: Profile):
    """Test resolve method."""
    assert await resolver.resolve(profile, TEST_DID)
