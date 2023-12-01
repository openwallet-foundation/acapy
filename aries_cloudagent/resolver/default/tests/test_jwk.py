"""Test JwkDIDResolver."""

import pytest

from ....core.in_memory import InMemoryProfile
from ....core.profile import Profile

from ...base import DIDMethodNotSupported
from ..jwk import JwkDIDResolver

# pylint: disable=W0621
TEST_DIDS = [
    "did:jwk:eyJjcnYiOiJQLTI1NiIsImt0eSI6IkVDIiwieCI6ImFjYklRaXVNczNpOF91c3pFakoydHBUdFJNNEVVM3l6OTFQSDZDZEgyVjAiLCJ5IjoiX0tjeUxqOXZXTXB0bm1LdG00NkdxRHo4d2Y3NEk1TEtncmwyR3pIM25TRSJ9",
    "did:jwk:eyJrdHkiOiJPS1AiLCJjcnYiOiJYMjU1MTkiLCJ1c2UiOiJlbmMiLCJ4IjoiM3A3YmZYdDl3YlRUVzJIQzdPUTFOei1EUThoYmVHZE5yZngtRkctSUswOCJ9",
]

TEST_DID_INVALID = "did:key:z1MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th"


@pytest.fixture
def resolver():
    """Resolver fixture."""
    yield JwkDIDResolver()


@pytest.fixture
def profile():
    """Profile fixture."""
    profile = InMemoryProfile.test_profile()
    yield profile


@pytest.mark.asyncio
@pytest.mark.parametrize("did", TEST_DIDS)
async def test_supported_did_regex(profile, resolver: JwkDIDResolver, did: str):
    """Test the supported_did_regex."""
    assert await resolver.supports(
        profile,
        did,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("did", TEST_DIDS)
async def test_resolve(resolver: JwkDIDResolver, profile: Profile, did: str):
    """Test resolve method."""
    assert await resolver.resolve(profile, did)


@pytest.mark.asyncio
async def test_resolve_x_did_not_found(resolver: JwkDIDResolver, profile: Profile):
    """Test resolve method when no did is found."""
    with pytest.raises(DIDMethodNotSupported):
        await resolver.resolve(profile, TEST_DID_INVALID)
