"""Test PeerDIDResolver."""

from asynctest import mock as async_mock
from peerdid.dids import resolve_peer_did
import pydid
import pytest

from .. import legacy_peer as test_module
from ....cache.base import BaseCache
from ....cache.in_memory import InMemoryCache
from ....connections.models.diddoc.diddoc import DIDDoc
from ....core.in_memory import InMemoryProfile
from ....core.profile import Profile
from ....storage.error import StorageNotFoundError
from ..legacy_peer import LegacyPeerDIDResolver


TEST_DID0 = "did:peer:2.Ez6LSpkcni2KTTxf4nAp6cPxjRbu26Tj4b957BgHcknVeNFEj.Vz6MksXhfmxm2i3RnoHH2mKQcx7EY4tToJR9JziUs6bp8a6FM.SeyJ0IjoiZGlkLWNvbW11bmljYXRpb24iLCJzIjoiaHR0cDovL2hvc3QuZG9ja2VyLmludGVybmFsOjkwNzAiLCJyZWNpcGllbnRfa2V5cyI6W119"
TEST_DID0_DOC = resolve_peer_did(TEST_DID0).dict()

@pytest.fixture
def resolver():
    """Resolver fixture."""
    yield LegacyPeerDIDResolver()


@pytest.fixture
def profile():
    """Profile fixture."""
    profile = InMemoryProfile.test_profile()
    profile.context.injector.bind_instance(BaseCache, InMemoryCache())
    yield profile


class TestPeerDIDResolver:
    @pytest.mark.asyncio
    async def test_supports(self, resolver: LegacyPeerDIDResolver, profile: Profile):
        """Test supports."""
        with async_mock.patch.object(test_module, "BaseConnectionManager") as mock_mgr:
            mock_mgr.return_value = async_mock.MagicMock(
                fetch_did_document=async_mock.CoroutineMock(
                    return_value=(TEST_DID0_DOC, None)
                )
            )
            assert await resolver.supports(profile, TEST_DID0)

    @pytest.mark.asyncio
    async def test_supports_no_cache(
        self, resolver: LegacyPeerDIDResolver, profile: Profile
    ):
        """Test supports."""
        profile.context.injector.clear_binding(BaseCache)
        with async_mock.patch.object(test_module, "BaseConnectionManager") as mock_mgr:
            mock_mgr.return_value = async_mock.MagicMock(
                fetch_did_document=async_mock.CoroutineMock(
                    return_value=(TEST_DID0_DOC, None)
                )
            )
            assert await resolver.supports(profile, TEST_DID0)