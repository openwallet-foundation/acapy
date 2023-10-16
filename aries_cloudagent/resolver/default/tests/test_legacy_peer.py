"""Test LegacyPeerDIDResolver."""

from asynctest import mock as async_mock
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

    @pytest.mark.parametrize(
        ("input_doc", "expected"),
        [
            (  # Examples
                {
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
                            "recipientKeys": [
                                "AU2FFjtkVzjFuirgWieqGGqtNrAZWS9LDuB8TDp6EUrG"
                            ],
                            "routingKeys": [
                                "9NnKFUZoYcCqYC2PcaXH3cnaGsoRfyGgyEHbvbLJYh8j"
                            ],
                            "serviceEndpoint": "http://bob:3000",
                        }
                    ],
                },
                {
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
                            "id": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ#didcomm-0",
                            "type": "did-communication",
                            "priority": 0,
                            "recipientKeys": ["did:sov:JNKL9kJxQi5pNCfA8QBXdJ#1"],
                            "routingKeys": [
                                "did:key:z6Mknq3MqipEt9hJegs6J9V7tiLa6T5H5rX3fFCXksJKTuv7#z6Mknq3MqipEt9hJegs6J9V7tiLa6T5H5rX3fFCXksJKTuv7"
                            ],
                            "serviceEndpoint": "http://bob:3000",
                        }
                    ],
                },
            ),
            (  # Stored findy doc
                {
                    "@context": "https://w3id.org/did/v1",
                    "id": "did:sov:5qXMeLdyWEQhieFUBNw5ux",
                    "publicKey": [
                        {
                            "id": "did:sov:5qXMeLdyWEQhieFUBNw5ux#1",
                            "type": "Ed25519VerificationKey2018",
                            "controller": "did:sov:5qXMeLdyWEQhieFUBNw5ux",
                            "publicKeyBase58": "3dtu2WWtd5ELwRTJEPzmEJUYEp8Qq36N2QA24g9tFXK9",
                        }
                    ],
                    "authentication": [
                        {
                            "type": "Ed25519SignatureAuthentication2018",
                            "publicKey": "did:sov:5qXMeLdyWEQhieFUBNw5ux#1",
                        }
                    ],
                    "service": [
                        {
                            "id": "did:sov:5qXMeLdyWEQhieFUBNw5ux",
                            "type": "IndyAgent",
                            "priority": None,
                            "recipientKeys": [
                                "3dtu2WWtd5ELwRTJEPzmEJUYEp8Qq36N2QA24g9tFXK9"
                            ],
                            "serviceEndpoint": "http://172.17.0.1:9031/a2a/5b6dyY6PndLaCnWxZbeEYW/5b6dyY6PndLaCnWxZbeEYW/2f6aae0c-6b04-40ff-a25e-faecaea39f83",
                        }
                    ],
                },
                {
                    "@context": "https://w3id.org/did/v1",
                    "id": "did:sov:5qXMeLdyWEQhieFUBNw5ux",
                    "verificationMethod": [
                        {
                            "id": "did:sov:5qXMeLdyWEQhieFUBNw5ux#1",
                            "type": "Ed25519VerificationKey2018",
                            "controller": "did:sov:5qXMeLdyWEQhieFUBNw5ux",
                            "publicKeyBase58": "3dtu2WWtd5ELwRTJEPzmEJUYEp8Qq36N2QA24g9tFXK9",
                        }
                    ],
                    "authentication": ["did:sov:5qXMeLdyWEQhieFUBNw5ux#1"],
                    "service": [
                        {
                            "id": "did:sov:5qXMeLdyWEQhieFUBNw5ux#didcomm-0",
                            "type": "did-communication",
                            "recipientKeys": ["did:sov:5qXMeLdyWEQhieFUBNw5ux#1"],
                            "serviceEndpoint": "http://172.17.0.1:9031/a2a/5b6dyY6PndLaCnWxZbeEYW/5b6dyY6PndLaCnWxZbeEYW/2f6aae0c-6b04-40ff-a25e-faecaea39f83",
                        }
                    ],
                },
            ),
            (  # Stored afgo doc
                {
                    "@context": "https://w3id.org/did/v1",
                    "id": "did:sov:1H6d1WS29Bcfr7Bb9tZxA",
                    "publicKey": [
                        {
                            "id": "did:sov:1H6d1WS29Bcfr7Bb9tZxA#cSwsDbSW",
                            "type": "Ed25519VerificationKey2018",
                            "controller": "did:sov:1H6d1WS29Bcfr7Bb9tZxA",
                            "publicKeyBase58": "gMxdVMyF8RakaptxFsDzHAxfQ5iEKZkCEQcSwsDbSWf",
                        }
                    ],
                    "authentication": [],
                    "service": [
                        {
                            "id": "did:sov:1H6d1WS29Bcfr7Bb9tZxA;0f555a80-c950-4b2c-b8ec-632c72ffd780",
                            "type": "IndyAgent",
                            "priority": 0,
                            "recipientKeys": [
                                "gMxdVMyF8RakaptxFsDzHAxfQ5iEKZkCEQcSwsDbSWf"
                            ],
                            "serviceEndpoint": "http://172.17.0.1:9031",
                        }
                    ],
                },
                {
                    "@context": "https://w3id.org/did/v1",
                    "id": "did:sov:1H6d1WS29Bcfr7Bb9tZxA",
                    "verificationMethod": [
                        {
                            "id": "did:sov:1H6d1WS29Bcfr7Bb9tZxA#cSwsDbSW",
                            "type": "Ed25519VerificationKey2018",
                            "controller": "did:sov:1H6d1WS29Bcfr7Bb9tZxA",
                            "publicKeyBase58": "gMxdVMyF8RakaptxFsDzHAxfQ5iEKZkCEQcSwsDbSWf",
                        }
                    ],
                    "authentication": [],
                    "service": [
                        {
                            "id": "did:sov:1H6d1WS29Bcfr7Bb9tZxA#didcomm-0",
                            "type": "did-communication",
                            "priority": 0,
                            "recipientKeys": ["did:sov:1H6d1WS29Bcfr7Bb9tZxA#cSwsDbSW"],
                            "serviceEndpoint": "http://172.17.0.1:9031",
                        }
                    ],
                },
            ),
            (  # Stored doc with routing keys
                {
                    "@context": "https://w3id.org/did/v1",
                    "id": "did:sov:PkWfCgY4SSAYeSoaWx3RFP",
                    "publicKey": [
                        {
                            "id": "did:sov:PkWfCgY4SSAYeSoaWx3RFP#1",
                            "type": "Ed25519VerificationKey2018",
                            "controller": "did:sov:PkWfCgY4SSAYeSoaWx3RFP",
                            "publicKeyBase58": "DQBMbzLmAK5iyiuPnqNvfkx3CQ2iTJ2sKz98utvdET4K",
                        },
                        {
                            "id": "did:sov:PkWfCgY4SSAYeSoaWx3RFP#QPUs2fFT",
                            "type": "Ed25519VerificationKey2018",
                            "controller": "did:sov:PkWfCgY4SSAYeSoaWx3RFP",
                            "publicKeyBase58": "cK7fwfjpakMuv8QKVv2y6qouZddVw4TxZNQPUs2fFTd",
                        },
                    ],
                    "authentication": [
                        {
                            "type": "Ed25519SignatureAuthentication2018",
                            "publicKey": "did:sov:PkWfCgY4SSAYeSoaWx3RFP#1",
                        }
                    ],
                    "service": [
                        {
                            "id": "did:sov:PkWfCgY4SSAYeSoaWx3RFP;PkWfCgY4SSAYeSoaWx3RFP#IndyAgentService",
                            "type": "IndyAgent",
                            "priority": 0,
                            "recipientKeys": [
                                "DQBMbzLmAK5iyiuPnqNvfkx3CQ2iTJ2sKz98utvdET4K"
                            ],
                            "routingKeys": [
                                "cK7fwfjpakMuv8QKVv2y6qouZddVw4TxZNQPUs2fFTd"
                            ],
                            "serviceEndpoint": "https://aries-mediator-agent.vonx.io",
                        }
                    ],
                },
                {
                    "@context": "https://w3id.org/did/v1",
                    "id": "did:sov:PkWfCgY4SSAYeSoaWx3RFP",
                    "verificationMethod": [
                        {
                            "id": "did:sov:PkWfCgY4SSAYeSoaWx3RFP#1",
                            "type": "Ed25519VerificationKey2018",
                            "controller": "did:sov:PkWfCgY4SSAYeSoaWx3RFP",
                            "publicKeyBase58": "DQBMbzLmAK5iyiuPnqNvfkx3CQ2iTJ2sKz98utvdET4K",
                        }
                    ],
                    "authentication": ["did:sov:PkWfCgY4SSAYeSoaWx3RFP#1"],
                    "service": [
                        {
                            "id": "did:sov:PkWfCgY4SSAYeSoaWx3RFP#didcomm-0",
                            "type": "did-communication",
                            "priority": 0,
                            "recipientKeys": ["did:sov:PkWfCgY4SSAYeSoaWx3RFP#1"],
                            "routingKeys": [
                                "did:key:z6Mkf4aAGBvBA8Eq2Qy714sspCPoj8uUupJpeaHLDkq3aUF1#z6Mkf4aAGBvBA8Eq2Qy714sspCPoj8uUupJpeaHLDkq3aUF1"
                            ],
                            "serviceEndpoint": "https://aries-mediator-agent.vonx.io",
                        }
                    ],
                },
            ),
            (  # Stored bifold doc
                {
                    "@context": "https://w3id.org/did/v1",
                    "publicKey": [
                        {
                            "id": "PkWfCgY4SSAYeSoaWx3RFP#1",
                            "controller": "PkWfCgY4SSAYeSoaWx3RFP",
                            "type": "Ed25519VerificationKey2018",
                            "publicKeyBase58": "DQBMbzLmAK5iyiuPnqNvfkx3CQ2iTJ2sKz98utvdET4K",
                        }
                    ],
                    "service": [
                        {
                            "id": "PkWfCgY4SSAYeSoaWx3RFP#IndyAgentService",
                            "serviceEndpoint": "https://aries-mediator-agent.vonx.io",
                            "type": "IndyAgent",
                            "priority": 0,
                            "recipientKeys": [
                                "DQBMbzLmAK5iyiuPnqNvfkx3CQ2iTJ2sKz98utvdET4K"
                            ],
                            "routingKeys": [
                                "cK7fwfjpakMuv8QKVv2y6qouZddVw4TxZNQPUs2fFTd"
                            ],
                        }
                    ],
                    "authentication": [
                        {
                            "publicKey": "PkWfCgY4SSAYeSoaWx3RFP#1",
                            "type": "Ed25519SignatureAuthentication2018",
                        }
                    ],
                    "id": "PkWfCgY4SSAYeSoaWx3RFP",
                },
                {
                    "@context": "https://w3id.org/did/v1",
                    "id": "did:sov:PkWfCgY4SSAYeSoaWx3RFP",
                    "verificationMethod": [
                        {
                            "id": "did:sov:PkWfCgY4SSAYeSoaWx3RFP#1",
                            "type": "Ed25519VerificationKey2018",
                            "controller": "did:sov:PkWfCgY4SSAYeSoaWx3RFP",
                            "publicKeyBase58": "DQBMbzLmAK5iyiuPnqNvfkx3CQ2iTJ2sKz98utvdET4K",
                        }
                    ],
                    "authentication": ["did:sov:PkWfCgY4SSAYeSoaWx3RFP#1"],
                    "service": [
                        {
                            "id": "did:sov:PkWfCgY4SSAYeSoaWx3RFP#IndyAgentService",
                            "type": "did-communication",
                            "priority": 0,
                            "recipientKeys": ["did:sov:PkWfCgY4SSAYeSoaWx3RFP#1"],
                            "routingKeys": [
                                "did:key:z6Mkf4aAGBvBA8Eq2Qy714sspCPoj8uUupJpeaHLDkq3aUF1#z6Mkf4aAGBvBA8Eq2Qy714sspCPoj8uUupJpeaHLDkq3aUF1"
                            ],
                            "serviceEndpoint": "https://aries-mediator-agent.vonx.io",
                        }
                    ],
                },
            ),
            (  # Doc with multiple services
                {
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
                            "recipientKeys": [
                                "AU2FFjtkVzjFuirgWieqGGqtNrAZWS9LDuB8TDp6EUrG"
                            ],
                            "routingKeys": [
                                "9NnKFUZoYcCqYC2PcaXH3cnaGsoRfyGgyEHbvbLJYh8j"
                            ],
                            "serviceEndpoint": "http://bob:3000",
                        },
                        {
                            "id": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ;indy-ws",
                            "type": "IndyAgent",
                            "priority": 1,
                            "recipientKeys": [
                                "AU2FFjtkVzjFuirgWieqGGqtNrAZWS9LDuB8TDp6EUrG"
                            ],
                            "routingKeys": [
                                "9NnKFUZoYcCqYC2PcaXH3cnaGsoRfyGgyEHbvbLJYh8j"
                            ],
                            "serviceEndpoint": "ws://bob:3000",
                        },
                    ],
                },
                {
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
                            "id": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ#didcomm-0",
                            "type": "did-communication",
                            "priority": 0,
                            "recipientKeys": ["did:sov:JNKL9kJxQi5pNCfA8QBXdJ#1"],
                            "routingKeys": [
                                "did:key:z6Mknq3MqipEt9hJegs6J9V7tiLa6T5H5rX3fFCXksJKTuv7#z6Mknq3MqipEt9hJegs6J9V7tiLa6T5H5rX3fFCXksJKTuv7"
                            ],
                            "serviceEndpoint": "http://bob:3000",
                        },
                        {
                            "id": "did:sov:JNKL9kJxQi5pNCfA8QBXdJ#didcomm-1",
                            "type": "did-communication",
                            "priority": 1,
                            "recipientKeys": ["did:sov:JNKL9kJxQi5pNCfA8QBXdJ#1"],
                            "routingKeys": [
                                "did:key:z6Mknq3MqipEt9hJegs6J9V7tiLa6T5H5rX3fFCXksJKTuv7#z6Mknq3MqipEt9hJegs6J9V7tiLa6T5H5rX3fFCXksJKTuv7"
                            ],
                            "serviceEndpoint": "ws://bob:3000",
                        },
                    ],
                },
            ),
        ],
    )
    def test_corrections(self, input_doc: dict, expected: dict):
        actual = test_module.LegacyDocCorrections.apply(input_doc)
        assert actual == expected
        assert expected == test_module.LegacyDocCorrections.apply(expected)
        doc = pydid.deserialize_document(actual)
        assert doc.service
        assert isinstance(doc.service[0], pydid.DIDCommService)

    @pytest.mark.parametrize(
        ("input_doc", "expected"),
        [
            (
                {
                    "@context": "https://w3id.org/did/v1",
                    "id": "StwSYX1WFcJ7MBfYWxmuQ9",
                    "publicKey": [
                        {
                            "type": "Ed25519VerificationKey2018",
                            "id": "StwSYX1WFcJ7MBfYWxmuQ9#1",
                            "controller": "StwSYX1WFcJ7MBfYWxmuQ9",
                            "publicKeyBase58": "F7cEyTgzUbFwHsTwC2cK2Zy8bdraeoMY8921gyDmefwK",
                        }
                    ],
                    "authentication": [
                        {
                            "type": "Ed25519VerificationKey2018",
                            "publicKey": "StwSYX1WFcJ7MBfYWxmuQ9#1",
                        }
                    ],
                    "service": [
                        {
                            "type": "IndyAgent",
                            "id": "StwSYX1WFcJ7MBfYWxmuQ9#IndyAgentService",
                            "serviceEndpoint": "https://example.com/endpoint",
                            "recipientKeys": [
                                "F7cEyTgzUbFwHsTwC2cK2Zy8bdraeoMY8921gyDmefwK"
                            ],
                            "routingKeys": [
                                "did:key:z6Mko2LnynhGbkPQdZ3PQBUgCmrzdH9aJe7HTs4LKontx8Ge"
                            ],
                        }
                    ],
                },
                {
                    "@context": "https://w3id.org/did/v1",
                    "id": "did:sov:StwSYX1WFcJ7MBfYWxmuQ9",
                    "verificationMethod": [
                        {
                            "type": "Ed25519VerificationKey2018",
                            "id": "did:sov:StwSYX1WFcJ7MBfYWxmuQ9#1",
                            "controller": "did:sov:StwSYX1WFcJ7MBfYWxmuQ9",
                            "publicKeyBase58": "F7cEyTgzUbFwHsTwC2cK2Zy8bdraeoMY8921gyDmefwK",
                        }
                    ],
                    "authentication": ["did:sov:StwSYX1WFcJ7MBfYWxmuQ9#1"],
                    "service": [
                        {
                            "id": "did:sov:StwSYX1WFcJ7MBfYWxmuQ9#didcomm-0",
                            "type": "did-communication",
                            "serviceEndpoint": "https://example.com/endpoint",
                            "recipientKeys": ["did:sov:StwSYX1WFcJ7MBfYWxmuQ9#1"],
                            "routingKeys": [
                                "did:key:z6Mko2LnynhGbkPQdZ3PQBUgCmrzdH9aJe7HTs4LKontx8Ge#z6Mko2LnynhGbkPQdZ3PQBUgCmrzdH9aJe7HTs4LKontx8Ge"
                            ],
                        }
                    ],
                },
            )
        ],
    )
    def test_corrections_on_doc_as_received(self, input_doc: dict, expected: dict):
        parsed = DIDDoc.deserialize(input_doc)
        actual = test_module.LegacyDocCorrections.apply(parsed.serialize())
        assert actual == expected
        assert expected == test_module.LegacyDocCorrections.apply(expected)
        doc = pydid.deserialize_document(actual)
        assert doc.service
        assert isinstance(doc.service[0], pydid.DIDCommService)
