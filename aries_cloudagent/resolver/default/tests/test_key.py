"""Test KeyDIDResolver."""

import pytest

from ....core.in_memory import InMemoryProfile
from ....core.profile import Profile
from ...base import DIDNotFound
from ..key import KeyDIDResolver

# pylint: disable=W0621
TEST_DID0 = "did:key:z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th"
TEST_DID_INVALID = "did:key:z1MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th"


@pytest.fixture
def resolver():
    """Resolver fixture."""
    yield KeyDIDResolver()


@pytest.fixture
def profile():
    """Profile fixture."""
    profile = InMemoryProfile.test_profile()
    yield profile


def test_supported_methods(resolver: KeyDIDResolver):
    """Test the supported_methods."""
    assert resolver.supported_methods == ["key"]
    assert resolver.supports("key")


@pytest.mark.asyncio
async def test_resolve(resolver: KeyDIDResolver, profile: Profile):
    """Test resolve method."""
    assert await resolver.resolve(profile, TEST_DID0)


@pytest.mark.asyncio
async def test_resolve_x_did_not_found(resolver: KeyDIDResolver, profile: Profile):
    """Test resolve method when no did is found."""
    with pytest.raises(DIDNotFound):
        await resolver.resolve(profile, TEST_DID_INVALID)
