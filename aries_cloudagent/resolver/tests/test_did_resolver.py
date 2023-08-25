"""Test did resolver registry."""

from typing import Pattern

import re

import pytest

from asynctest import mock as async_mock
from pydid import DID, DIDDocument, VerificationMethod, BasicDIDDocument

from ...core.in_memory import InMemoryProfile
from ..base import (
    BaseDIDResolver,
    DIDMethodNotSupported,
    DIDNotFound,
    ResolutionMetadata,
    ResolverError,
    ResolverType,
)
from ..did_resolver import DIDResolver

from . import DOC

TEST_DID0 = "did:sov:Kkyqu7CJFuQSvBp468uaDe"
TEST_DID1 = "did:btcr:8kyt-fzzq-qpqq-ljsc-5l"
TEST_DID2 = "did:ethr:mainnet:0xb9c5714089478a327f09197987f16f9e5d936e8a"
TEST_DID3 = "did:ion:EiDahaOGH-liLLdDtTxEAdc8i-cfCz-WUcQdRJheMVNn3A"
TEST_DID4 = "did:github:ghdid"
TEST_DID_5 = "did:key:zUC71nmwvy83x1UzNKbZbS7N9QZx8rqpQx3Ee3jGfKiEkZngTKzsRoqobX6wZdZF5F93pSGYYco3gpK9tc53ruWUo2tkBB9bxPCFBUjq2th8FbtT4xih6y6Q1K9EL4Th86NiCGT"

TEST_DIDS = [TEST_DID0, TEST_DID1, TEST_DID2, TEST_DID3, TEST_DID4, TEST_DID_5]

TEST_DID_METHOD0 = "sov"
TEST_DID_METHOD1 = "btcr"
TEST_DID_METHOD2 = "ethr"
TEST_DID_METHOD3 = "ion"
TEST_DID_METHOD4 = "github"
TEST_DID_METHOD5 = "key"

TEST_DID_METHODS = [
    TEST_DID_METHOD0,
    TEST_DID_METHOD1,
    TEST_DID_METHOD2,
    TEST_DID_METHOD3,
    TEST_DID_METHOD4,
    TEST_DID_METHOD5,
    "example",
]

TEST_METHOD_SPECIFIC_ID0 = "Kkyqu7CJFuQSvBp468uaDe"
TEST_METHOD_SPECIFIC_ID1 = "8kyt-fzzq-qpqq-ljsc-5l"
TEST_METHOD_SPECIFIC_ID2 = "mainnet:0xb9c5714089478a327f09197987f16f9e5d936e8a"
TEST_METHOD_SPECIFIC_ID3 = "EiDahaOGH-liLLdDtTxEAdc8i-cfCz-WUcQdRJheMVNn3A"
TEST_METHOD_SPECIFIC_ID4 = "ghdid"
TEST_METHOD_SPECIFIC_ID5 = "zUC71nmwvy83x1UzNKbZbS7N9QZx8rqpQx3Ee3jGfKiEkZngTKzsRoqobX6wZdZF5F93pSGYYco3gpK9tc53ruWUo2tkBB9bxPCFBUjq2th8FbtT4xih6y6Q1K9EL4Th86NiCGT"

TEST_METHOD_SPECIFIC_IDS = [
    TEST_METHOD_SPECIFIC_ID0,
    TEST_METHOD_SPECIFIC_ID1,
    TEST_METHOD_SPECIFIC_ID2,
    TEST_METHOD_SPECIFIC_ID3,
    TEST_METHOD_SPECIFIC_ID4,
    TEST_METHOD_SPECIFIC_ID5,
]


class MockResolver(BaseDIDResolver):
    def __init__(self, supported_methods, resolved=None, native: bool = False):
        super().__init__(ResolverType.NATIVE if native else ResolverType.NON_NATIVE)
        self._did_regex = re.compile(
            "^did:(?:{}):.*$".format("|".join(supported_methods))
        )
        self.resolved = resolved

    @property
    def supported_did_regex(self) -> Pattern:
        return self._did_regex

    async def setup(self, context):
        pass

    async def _resolve(self, profile, did, accept):
        if isinstance(self.resolved, Exception):
            raise self.resolved
        if isinstance(self.resolved, dict):
            return self.resolved
        return self.resolved.serialize()


@pytest.fixture
def resolver():
    did_resolver_registry = []
    for method in TEST_DID_METHODS:
        resolver = MockResolver([method], DIDDocument.deserialize(DOC))
        did_resolver_registry.append(resolver)
    return DIDResolver(did_resolver_registry)


@pytest.fixture
def profile():
    yield InMemoryProfile.test_profile()


def test_create_resolver(resolver):
    assert len(resolver.resolvers) == len(TEST_DID_METHODS)


@pytest.mark.asyncio
@pytest.mark.parametrize("did, method", zip(TEST_DIDS, TEST_DID_METHODS))
async def test_match_did_to_resolver(profile, resolver, did, method):
    base_resolver, *_ = await resolver._match_did_to_resolver(profile, did)
    assert await base_resolver.supports(profile, did)


@pytest.mark.asyncio
async def test_match_did_to_resolver_x_not_supported(resolver):
    with pytest.raises(DIDMethodNotSupported):
        await resolver._match_did_to_resolver(
            profile, "did:cowsay:EiDahaOGH-liLLdDtTxEAdc8i-cfCz-WUcQdRJheMVNn3A"
        )


@pytest.mark.asyncio
async def test_match_did_to_resolver_native_priority(profile):
    native = MockResolver(["sov"], native=True)
    non_native = MockResolver(["sov"], native=False)
    registry = [non_native, native]
    resolver = DIDResolver(registry)
    assert [native, non_native] == await resolver._match_did_to_resolver(
        profile, TEST_DID0
    )


@pytest.mark.asyncio
async def test_match_did_to_resolver_registration_order(profile):
    native1 = MockResolver(["sov"], native=True)
    native2 = MockResolver(["sov"], native=True)
    non_native3 = MockResolver(["sov"], native=False)
    native4 = MockResolver(["sov"], native=True)
    registry = [native1, native2, non_native3, native4]
    resolver = DIDResolver(registry)
    assert [
        native1,
        native2,
        native4,
        non_native3,
    ] == await resolver._match_did_to_resolver(profile, TEST_DID0)


@pytest.mark.asyncio
async def test_dereference(resolver, profile):
    url = "did:example:1234abcd#4"
    expected: dict = DOC["verificationMethod"][0]
    actual: VerificationMethod = await resolver.dereference(profile, url)
    assert expected == actual.serialize()


@pytest.mark.asyncio
async def test_dereference_diddoc(resolver, profile):
    url = "did:example:1234abcd#4"
    doc = BasicDIDDocument(
        id="did:example:z6Mkmpe2DyE4NsDiAb58d75hpi1BjqbH6wYMschUkjWDEEuR"
    )
    result = await resolver.dereference(profile, url, document=doc)
    assert isinstance(result, VerificationMethod)
    assert result.id == url


@pytest.mark.asyncio
async def test_dereference_x(resolver, profile):
    url = "non-did"
    with pytest.raises(ResolverError):
        await resolver.dereference(profile, url)


@pytest.mark.asyncio
@pytest.mark.parametrize("did", TEST_DIDS)
async def test_resolve_with_metadata(resolver, profile, did):
    result = await resolver.resolve_with_metadata(profile, did)
    assert isinstance(result.did_document, dict)
    assert isinstance(result.metadata, ResolutionMetadata)


@pytest.mark.asyncio
@pytest.mark.parametrize("did", TEST_DIDS)
async def test_resolve(resolver, profile, did):
    doc = await resolver.resolve(profile, did)
    assert isinstance(doc, dict)


@pytest.mark.asyncio
@pytest.mark.parametrize("did", TEST_DIDS)
async def test_resolve_did(resolver, profile, did):
    doc = await resolver.resolve(profile, DID(did))
    assert isinstance(doc, dict)


@pytest.mark.asyncio
async def test_resolve_did_x_not_supported(resolver, profile):
    py_did = DID("did:cowsay:EiDahaOGH-liLLdDtTxEAdc8i-cfCz-WUcQdRJheMVNn3A")
    with pytest.raises(DIDMethodNotSupported):
        await resolver.resolve(profile, py_did)


@pytest.mark.asyncio
async def test_resolve_did_x_not_found(profile):
    py_did = DID("did:cowsay:EiDahaOGH-liLLdDtTxEAdc8i-cfCz-WUcQdRJheMVNn3A")
    cowsay_resolver_not_found = MockResolver(["cowsay"], resolved=DIDNotFound())
    resolver = DIDResolver([cowsay_resolver_not_found])
    with pytest.raises(DIDNotFound):
        await resolver.resolve(profile, py_did)
