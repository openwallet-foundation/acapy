"""Test did resolver registery."""

import pytest
import unittest
from asynctest import mock as async_mock
from ..did_resolver_registry import DIDResolverRegistry
from ..did_resolver import DIDResolver
from ...resolver.diddoc import ResolvedDIDDoc
from ...resolver.did import DID


TEST_DID0 = "did:sov:Kkyqu7CJFuQSvBp468uaDe"
TEST_DID1 = "did:btcr:8kyt-fzzq-qpqq-ljsc-5l"
TEST_DID2 = "did:ethr:mainnet:0xb9c5714089478a327f09197987f16f9e5d936e8a"
TEST_DID3 = "did:ion:EiDahaOGH-liLLdDtTxEAdc8i-cfCz-WUcQdRJheMVNn3A"
TEST_DID4 = "did:github:ghdid"

TEST_DIDS = [
    TEST_DID0,
    TEST_DID1,
    TEST_DID2,
    TEST_DID3,
    TEST_DID4,
]

TEST_DID_METHOD0 = "sov"
TEST_DID_METHOD1 = "btcr"
TEST_DID_METHOD2 = "ethr"
TEST_DID_METHOD3 = "ion"
TEST_DID_METHOD4 = "github"

TEST_DID_METHODS = [
    TEST_DID_METHOD0,
    TEST_DID_METHOD1,
    TEST_DID_METHOD2,
    TEST_DID_METHOD3,
    TEST_DID_METHOD4,
]

TEST_METHOD_SPECIFIC_ID0 = "Kkyqu7CJFuQSvBp468uaDe"
TEST_METHOD_SPECIFIC_ID1 = "8kyt-fzzq-qpqq-ljsc-5l"
TEST_METHOD_SPECIFIC_ID2 = "mainnet:0xb9c5714089478a327f09197987f16f9e5d936e8a"
TEST_METHOD_SPECIFIC_ID3 = "EiDahaOGH-liLLdDtTxEAdc8i-cfCz-WUcQdRJheMVNn3A"
TEST_METHOD_SPECIFIC_ID4 = "ghdid"

TEST_METHOD_SPECIFIC_IDS = [
    TEST_METHOD_SPECIFIC_ID0,
    TEST_METHOD_SPECIFIC_ID1,
    TEST_METHOD_SPECIFIC_ID2,
    TEST_METHOD_SPECIFIC_ID3,
    TEST_METHOD_SPECIFIC_ID4,
]
did_resolver_registry = DIDResolverRegistry()
test_resolver_0 = unittest.mock.MagicMock()
test_resolver_0.supported_methods.return_value = [TEST_DID_METHOD0]
test_resolver_0.native.return_value = False
test_resolver_0.resolve.return_value = unittest.mock.MagicMock()
test_resolver_1 = unittest.mock.MagicMock()
test_resolver_1.supported_methods.return_value = [TEST_DID_METHOD1]
test_resolver_1.native.return_value = False
test_resolver_1.resolve.return_value = unittest.mock.MagicMock()
test_resolver_2 = unittest.mock.MagicMock()
test_resolver_2.supported_methods.return_value = [TEST_DID_METHOD2]
test_resolver_2.native.return_value = False
test_resolver_2.resolve.return_value = unittest.mock.MagicMock()
test_resolver_3 = unittest.mock.MagicMock()
test_resolver_3.supported_methods.return_value = [TEST_DID_METHOD3]
test_resolver_3.native.return_value = False
test_resolver_3.resolve.return_value = unittest.mock.MagicMock()
test_resolver_4 = unittest.mock.MagicMock()
test_resolver_4.supported_methods.return_value = [TEST_DID_METHOD4]
test_resolver_4.native.return_value = False
test_resolver_4.resolve.return_value = unittest.mock.MagicMock()
TEST_RESOLVERS = [
    test_resolver_0,
    test_resolver_1,
    test_resolver_2,
    test_resolver_3,
    test_resolver_4,
]


@pytest.fixture
def resolver():
    for resolver in TEST_RESOLVERS:
        did_resolver_registry.register(resolver)
    return DIDResolver(did_resolver_registry)


DOC = {
    "@context": "https://w3id.org/did/v1",
    "id": "did:example:1234abcd",
    "verificationMethod": [
        {
            "id": "3",
            "type": "RsaVerificationKey2018",
            "controller": "did:example:1234abcd",
            "publicKeyPem": "-----BEGIN PUBLIC X…",
        },
        {
            "id": "4",
            "type": "RsaVerificationKey2018",
            "controller": "did:example:1234abcd",
            "publicKeyPem": "-----BEGIN PUBLIC 9…",
        },
        {
            "id": "6",
            "type": "RsaVerificationKey2018",
            "controller": "did:example:1234abcd",
            "publicKeyPem": "-----BEGIN PUBLIC A…",
        },
    ],
    "authentication": [
        {
            "type": "RsaSignatureAuthentication2018",
            "publicKey": "did:example:1234abcd#4",
        }
    ],
    "service": [
        {
            "id": "did:example:123456789abcdefghi;did-communication",
            "type": "did-communication",
            "priority": 0,
            "recipientKeys": ["did:example:1234abcd#4"],
            "routingKeys": ["did:example:1234abcd#3"],
            "serviceEndpoint": "did:example:xd45fr567794lrzti67;did-communication",
        }
    ],
}


def test_create_resolver(resolver):
    assert len(resolver.did_resolver_registery.did_resolvers) == len(TEST_RESOLVERS)


@pytest.mark.parametrize("did, method", zip(TEST_DIDS, TEST_DID_METHODS))
def test_match_did_to_resolver(resolver, did, method):
    did = DID(did)
    base_resolver = next(resolver._match_did_to_resolver(did))
    assert base_resolver.supports(method)


def test_match_did_to_resolver_native_priority(resolver):
    pytest.skip("need more work")


@pytest.mark.parametrize("did", TEST_DIDS)
def test_dereference_external(resolver, did):
    with async_mock.patch.object(
        resolver, "resolve", async_mock.MagicMock(return_value="resolved did doc")
    ) as mock_resolver:
        result = mock_resolver.dereference_external(did)
        assert result


def test_fully_dereference(resolver):
    pytest.skip("need more work")


@pytest.mark.parametrize("did", TEST_DIDS)
async def test_resolve(resolver, did):
    did_doc = await resolver.resolve(did)
    assert did_doc
