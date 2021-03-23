"""Test did resolver registry."""

import unittest

import pytest
from asynctest import mock as async_mock

from ...resolver.base import (
    BaseDIDResolver,
    DIDMethodNotSupported,
    DIDNotFound,
    ResolverType,
)
from pydid import DID, DIDDocument, VerificationMethod
from . import DOC
from ..did_resolver import DIDResolver
from ..did_resolver_registry import DIDResolverRegistry

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
    "example",
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


class MockResolver(BaseDIDResolver):
    def __init__(self, supported_methods, resolved=None, native: bool = False):
        super().__init__(ResolverType.NATIVE if native else ResolverType.NON_NATIVE)
        self._supported_methods = supported_methods
        self.resolved = resolved

    async def setup(self, context):
        pass

    @property
    def supported_methods(self):
        return self._supported_methods

    async def _resolve(self, profile, did):
        if isinstance(self.resolved, Exception):
            raise self.resolved
        return self.resolved


@pytest.fixture
def resolver():
    did_resolver_registry = DIDResolverRegistry()
    for method in TEST_DID_METHODS:
        resolver = MockResolver([method], DIDDocument.deserialize(DOC))
        did_resolver_registry.register(resolver)
    return DIDResolver(did_resolver_registry)


@pytest.fixture
def profile():
    yield async_mock.MagicMock()


def test_create_resolver(resolver):
    assert len(resolver.did_resolver_registry.resolvers) == len(TEST_DID_METHODS)


@pytest.mark.parametrize("did, method", zip(TEST_DIDS, TEST_DID_METHODS))
def test_match_did_to_resolver(resolver, did, method):
    did = DID(did)
    base_resolver, *_ = resolver._match_did_to_resolver(did)
    assert base_resolver.supports(method)


def test_match_did_to_resolver_x_not_supported(resolver):
    did = DID("did:cowsay:EiDahaOGH-liLLdDtTxEAdc8i-cfCz-WUcQdRJheMVNn3A")
    with pytest.raises(DIDMethodNotSupported):
        resolver._match_did_to_resolver(did)


def test_match_did_to_resolver_native_priority():
    registry = DIDResolverRegistry()
    native = MockResolver(["sov"], native=True)
    non_native = MockResolver(["sov"], native=False)
    registry.register(non_native)
    registry.register(native)
    resolver = DIDResolver(registry)
    assert [native, non_native] == resolver._match_did_to_resolver(DID(TEST_DID0))


def test_match_did_to_resolver_registration_order():
    registry = DIDResolverRegistry()
    native1 = MockResolver(["sov"], native=True)
    registry.register(native1)
    native2 = MockResolver(["sov"], native=True)
    registry.register(native2)
    non_native3 = MockResolver(["sov"], native=False)
    registry.register(non_native3)
    native4 = MockResolver(["sov"], native=True)
    registry.register(native4)
    resolver = DIDResolver(registry)
    assert [native1, native2, native4, non_native3] == resolver._match_did_to_resolver(
        DID(TEST_DID0)
    )


@pytest.mark.asyncio
async def test_dereference(resolver, profile):
    url = "did:example:1234abcd#4"
    expected: dict = DOC["verificationMethod"][0]
    actual: VerificationMethod = await resolver.dereference(profile, url)
    assert expected == actual.serialize()


@pytest.mark.asyncio
@pytest.mark.parametrize("did", TEST_DIDS)
async def test_resolve(resolver, profile, did):
    did_doc = await resolver.resolve(profile, did)
    assert isinstance(did_doc, DIDDocument)


@pytest.mark.asyncio
@pytest.mark.parametrize("did", TEST_DIDS)
async def test_resolve_did(resolver, profile, did):
    did = DID(did)
    did_doc = await resolver.resolve(profile, did)
    assert isinstance(did_doc, DIDDocument)


@pytest.mark.asyncio
async def test_resolve_did_x_not_supported(resolver, profile):
    did = DID("did:cowsay:EiDahaOGH-liLLdDtTxEAdc8i-cfCz-WUcQdRJheMVNn3A")
    with pytest.raises(DIDMethodNotSupported):
        await resolver.resolve(profile, did)


@pytest.mark.asyncio
async def test_resolve_did_x_not_found(profile):
    did = DID("did:cowsay:EiDahaOGH-liLLdDtTxEAdc8i-cfCz-WUcQdRJheMVNn3A")
    cowsay_resolver_not_found = MockResolver("cowsay", resolved=DIDNotFound())
    registry = DIDResolverRegistry()
    registry.register(cowsay_resolver_not_found)
    resolver = DIDResolver(registry)
    with pytest.raises(DIDNotFound):
        await resolver.resolve(profile, did)
