"""Test did resolver registery."""

import pytest
import unittest
from ..did_resolver_registry import DIDResolverRegistry
from ..did_resolver import DIDResolver
from ...resolver.diddoc import ResolvedDIDDoc


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
test_resolver_1 = unittest.mock.MagicMock()
test_resolver_1.supported_methods.return_value = [TEST_DID_METHOD1]
test_resolver_2 = unittest.mock.MagicMock()
test_resolver_2.supported_methods.return_value = [TEST_DID_METHOD2]
test_resolver_3 = unittest.mock.MagicMock()
test_resolver_3.supported_methods.return_value = [TEST_DID_METHOD3]
test_resolver_4 = unittest.mock.MagicMock()
test_resolver_4.supported_methods.return_value = [TEST_DID_METHOD4]
TEST_RESOLVERS = [
    test_resolver_0,
    test_resolver_1,
    test_resolver_2,
    test_resolver_3,
    test_resolver_4,
]
for resolver in resolvers:
    did_resolver_registry.register(resolver)

resolver = DIDResolver(did_resolver_registry)


def test_create_resolver():
    assert resolver.did_resolver_registery == TEST_RESOLVERS


@pytest.mark.parametrize("did, method", zip(TEST_DIDS, TEST_DID_METHODS))
def test_match_did_to_resolver(did, method):
    base_resolver = resolver._match_did_to_resolver(did)
    assert base_resolver.supports(method)


def test_match_did_to_resolver_native_priority():
    pass


def test_dereference(did):
    pass


def test_fully_dereference(doc):
    pass


@pytest.mark.parametrize("did", TEST_DIDS)
def test_resolve(did):
    did = resolver.resolve(did)
    assert isinstance(did, ResolvedDIDDoc)
