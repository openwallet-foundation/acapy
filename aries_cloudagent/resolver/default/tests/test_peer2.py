"""Test PeerDIDResolver."""

from asynctest import mock as async_mock
from peerdid.dids import resolve_peer_did, DIDDocument, DID
import pytest

from .. import legacy_peer as test_module
from ....cache.base import BaseCache
from ....cache.in_memory import InMemoryCache
from ....core.in_memory import InMemoryProfile
from ....core.profile import Profile
from ...did_resolver import DIDResolver
from ..peer2 import PeerDID2Resolver, _resolve_peer_did_with_service_key_reference


TEST_DID0 = "did:peer:2.Ez6LSpkcni2KTTxf4nAp6cPxjRbu26Tj4b957BgHcknVeNFEj.Vz6MksXhfmxm2i3RnoHH2mKQcx7EY4tToJR9JziUs6bp8a6FM.SeyJ0IjoiZGlkLWNvbW11bmljYXRpb24iLCJzIjoiaHR0cDovL2hvc3QuZG9ja2VyLmludGVybmFsOjkwNzAiLCJyZWNpcGllbnRfa2V5cyI6W119"
TEST_DID0_DOC = _resolve_peer_did_with_service_key_reference(TEST_DID0).dict()
TEST_DID0_RAW_DOC = resolve_peer_did(TEST_DID0).dict()


@pytest.fixture
def common_resolver():
    """Resolver fixture."""
    yield DIDResolver([PeerDID2Resolver()])


@pytest.fixture
def resolver():
    """Resolver fixture."""
    yield PeerDID2Resolver()


@pytest.fixture
def profile():
    """Profile fixture."""
    profile = InMemoryProfile.test_profile()
    profile.context.injector.bind_instance(BaseCache, InMemoryCache())
    yield profile


class TestPeerDID2Resolver:
    @pytest.mark.asyncio
    async def test_resolution_types(self, resolver: PeerDID2Resolver, profile: Profile):
        """Test supports."""
        assert DID.is_valid(TEST_DID0)
        assert isinstance(resolve_peer_did(TEST_DID0), DIDDocument)
        assert isinstance(
            _resolve_peer_did_with_service_key_reference(TEST_DID0), DIDDocument
        )

    @pytest.mark.asyncio
    async def test_supports(self, resolver: PeerDID2Resolver, profile: Profile):
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
        self, resolver: PeerDID2Resolver, profile: Profile
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

    @pytest.mark.asyncio
    async def test_supports_service_referenced(
        self, resolver: PeerDID2Resolver, common_resolver: DIDResolver, profile: Profile
    ):
        """Test supports."""
        profile.context.injector.clear_binding(BaseCache)
        with async_mock.patch.object(test_module, "BaseConnectionManager") as mock_mgr:
            mock_mgr.return_value = async_mock.MagicMock(
                fetch_did_document=async_mock.CoroutineMock(
                    return_value=(TEST_DID0_DOC, None)
                )
            )
            recipient_key = await common_resolver.dereference(
                profile,
                TEST_DID0_DOC["service"][0]["recipient_keys"][0],
                document=DIDDocument.deserialize(TEST_DID0_DOC),
            )
            assert recipient_key
