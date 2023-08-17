"""Test LegacyPeerDIDResolver."""

from asynctest import mock as async_mock
import pytest

from .. import legacy_peer as test_module
from ....cache.base import BaseCache
from ....cache.in_memory import InMemoryCache
from ....connections.models.diddoc.diddoc import DIDDoc
from ....core.in_memory import InMemoryProfile
from ....core.profile import Profile
from ....storage.error import StorageNotFoundError
from ..legacy_peer import LegacyPeerDIDResolver


TEST_DID0 = "did:sov:WgWxqztrNooG92RXvxSTWv"
TEST_DID1 = "did:example:abc123"
TEST_DID2 = "did:sov:5No7f9KvpsfSqd6xsGxABh"


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


class TestLegacyPeerDIDResolver:
    @pytest.mark.asyncio
    async def test_supports(self, resolver: LegacyPeerDIDResolver, profile: Profile):
        """Test supports."""
        with async_mock.patch.object(test_module, "BaseConnectionManager") as mock_mgr:
            mock_mgr.return_value = async_mock.MagicMock(
                fetch_did_document=async_mock.CoroutineMock(
                    return_value=(DIDDoc(TEST_DID0), None)
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
                    return_value=(DIDDoc(TEST_DID0), None)
                )
            )
            assert await resolver.supports(profile, TEST_DID0)

    @pytest.mark.asyncio
    async def test_supports_x_not_legacy_did(
        self, resolver: LegacyPeerDIDResolver, profile: Profile
    ):
        """Test supports returns false for DID not matching legacy."""
        assert not await resolver.supports(profile, TEST_DID1)

    @pytest.mark.asyncio
    async def test_supports_x_unknown_did(
        self, resolver: LegacyPeerDIDResolver, profile: Profile
    ):
        """Test supports returns false for unknown DID."""
        with async_mock.patch.object(test_module, "BaseConnectionManager") as mock_mgr:
            mock_mgr.return_value = async_mock.MagicMock(
                fetch_did_document=async_mock.CoroutineMock(
                    side_effect=StorageNotFoundError
                )
            )
            assert not await resolver.supports(profile, TEST_DID2)

    @pytest.mark.asyncio
    async def test_resolve(self, resolver: LegacyPeerDIDResolver, profile: Profile):
        """Test resolve."""
        with async_mock.patch.object(
            test_module, "BaseConnectionManager"
        ) as mock_mgr, async_mock.patch.object(
            test_module, "LegacyDocCorrections"
        ) as mock_corrections:
            doc = object()
            mock_corrections.apply = async_mock.MagicMock(return_value=doc)
            mock_mgr.return_value = async_mock.MagicMock(
                fetch_did_document=async_mock.CoroutineMock(
                    return_value=(DIDDoc(TEST_DID0), None)
                )
            )
            result = await resolver.resolve(profile, TEST_DID0)
            assert result == doc

    @pytest.mark.asyncio
    async def test_resolve_x_not_found(
        self, resolver: LegacyPeerDIDResolver, profile: Profile
    ):
        """Test resolve with not found.

        This should be impossible in practice but still.
        """
        with async_mock.patch.object(
            test_module, "BaseConnectionManager"
        ) as mock_mgr, async_mock.patch.object(
            test_module, "LegacyDocCorrections"
        ) as mock_corrections, pytest.raises(
            test_module.DIDNotFound
        ):
            doc = object
            mock_corrections.apply = async_mock.MagicMock(return_value=doc)
            mock_mgr.return_value = async_mock.MagicMock(
                fetch_did_document=async_mock.CoroutineMock(
                    side_effect=StorageNotFoundError
                )
            )
            resolver.supports = async_mock.CoroutineMock(return_value=True)
            result = await resolver.resolve(profile, TEST_DID0)
            assert result == doc

    def test_corrections_examples(self):
        input_doc = {
            "@context": "https://w3id.org/did/v1",
            "id": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ",
            "publicKey": [
                {
                    "id": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ#1",
                    "type": "Ed25519VerificationKey2018",
                    "controller": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ",
                    "publicKeyBase58": "AU2FFjtkVzjFuirgWieqGGqtNrAZWS9LDuB8TDp6EUrG",
                }
            ],
            "authentication": [
                {
                    "type": "Ed25519SignatureAuthentication2018",
                    "publicKey": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ#1",
                }
            ],
            "service": [
                {
                    "id": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ;indy",
                    "type": "IndyAgent",
                    "priority": 0,
                    "recipientKeys": ["AU2FFjtkVzjFuirgWieqGGqtNrAZWS9LDuB8TDp6EUrG"],
                    "routingKeys": ["9NnKFUZoYcCqYC2PcaXH3cnaGsoRfyGgyEHbvbLJYh8j"],
                    "serviceEndpoint": "http://bob:3000",
                }
            ],
        }
        expected = {
            "@context": "https://w3id.org/did/v1",
            "id": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ",
            "verificationMethod": [
                {
                    "id": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ#1",
                    "type": "Ed25519VerificationKey2018",
                    "controller": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ",
                    "publicKeyBase58": "AU2FFjtkVzjFuirgWieqGGqtNrAZWS9LDuB8TDp6EUrG",
                }
            ],
            "authentication": ["did:sov:JNKL9kJxQi5pNCfA8QBXdJ#1"],
            "service": [
                {
                    "id": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ#didcomm",
                    "type": "did-communication",
                    "priority": 0,
                    "recipientKeys": ["did:sov:JNKL9kJxQi5pNCfA8QBXdJ#1"],
                    "routingKeys": [
                        "did:key:z6Mknq3MqipEt9hJegs6J9V7tiLa6T5H5rX3fFCXksJKTuv7#z6Mknq3MqipEt9hJegs6J9V7tiLa6T5H5rX3fFCXksJKTuv7"
                    ],
                    "serviceEndpoint": "http://bob:3000",
                }
            ],
        }
        actual = test_module.LegacyDocCorrections.apply(input_doc)
        assert actual == expected
        assert expected == test_module.LegacyDocCorrections.apply(expected)
