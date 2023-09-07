"""Test PeerDIDResolver."""

from hashlib import sha256
from peerdid.keys import to_multibase, MultibaseFormat

from asynctest import mock as async_mock
from peerdid.dids import DIDDocument, DID
import pytest

from .. import peer3 as test_module
from ....cache.base import BaseCache
from ....cache.in_memory import InMemoryCache
from ....core.in_memory import InMemoryProfile
from ....core.profile import Profile
from ...did_resolver import DIDResolver
from ..peer2 import _resolve_peer_did_with_service_key_reference
from ..peer3 import PeerDID3Resolver, _convert_to_did_peer_3_document


TEST_DP2 = "did:peer:2.Ez6LSpkcni2KTTxf4nAp6cPxjRbu26Tj4b957BgHcknVeNFEj.Vz6MksXhfmxm2i3RnoHH2mKQcx7EY4tToJR9JziUs6bp8a6FM.SeyJ0IjoiZGlkLWNvbW11bmljYXRpb24iLCJzIjoiaHR0cDovL2hvc3QuZG9ja2VyLmludGVybmFsOjkwNzAiLCJyZWNpcGllbnRfa2V5cyI6W119"
TEST_DID0_DOC = _resolve_peer_did_with_service_key_reference(TEST_DP2)

TEST_DP3 = DID(
    "did:peer:3"
    + to_multibase(
        sha256(TEST_DP2.lstrip("did:peer:2").encode()).digest(), MultibaseFormat.BASE58
    )
)
TEST_DP3_DOC = _convert_to_did_peer_3_document(TEST_DID0_DOC)


@pytest.fixture
def common_resolver():
    """Resolver fixture."""
    yield DIDResolver([PeerDID3Resolver()])


@pytest.fixture
def resolver():
    """Resolver fixture."""
    yield PeerDID3Resolver()


@pytest.fixture
def profile():
    """Profile fixture."""
    profile = InMemoryProfile.test_profile()
    profile.context.injector.bind_instance(BaseCache, InMemoryCache())
    yield profile


class TestPeerDID3Resolver:
    @pytest.mark.asyncio
    async def test_resolution_types(self, resolver: PeerDID3Resolver, profile: Profile):
        """Test supports."""
        assert DID.is_valid(TEST_DP3)
        assert isinstance(TEST_DP3_DOC, DIDDocument)
        assert TEST_DP3_DOC.id == TEST_DP3

    @pytest.mark.asyncio
    async def test_supports(self, resolver: PeerDID3Resolver, profile: Profile):
        """Test supports."""
        with async_mock.patch.object(test_module, "PeerDID3Resolver") as mock_resolve:
            mock_resolve.return_value = async_mock.MagicMock(
                _resolve=async_mock.CoroutineMock(return_value=TEST_DP3_DOC)
            )
            assert await resolver.supports(profile, TEST_DP3)

    @pytest.mark.asyncio
    async def test_supports_no_cache(
        self, resolver: PeerDID3Resolver, profile: Profile
    ):
        """Test supports."""
        profile.context.injector.clear_binding(BaseCache)
        with async_mock.patch.object(test_module, "PeerDID3Resolver") as mock_resolve:
            mock_resolve.return_value = async_mock.MagicMock(
                _resolve=async_mock.CoroutineMock(return_value=TEST_DP3_DOC)
            )
            assert await resolver.supports(profile, TEST_DP3)

    @pytest.mark.asyncio
    async def test_supports_service_referenced(
        self, resolver: PeerDID3Resolver, common_resolver: DIDResolver, profile: Profile
    ):
        """Test supports."""
        profile.context.injector.clear_binding(BaseCache)

        recipient_key = await common_resolver.dereference(
            profile,
            TEST_DP3_DOC.dict()["service"][0]["recipient_keys"][0],
            document=TEST_DP3_DOC,
        )
        assert recipient_key
