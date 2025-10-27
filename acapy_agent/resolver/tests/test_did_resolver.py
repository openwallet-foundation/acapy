"""Test did resolver registry."""

import re
from typing import Pattern

import pytest
import pytest_asyncio
from pydid import DID, BasicDIDDocument, DIDDocument, VerificationMethod

from ...utils.testing import create_test_profile
from ..base import (
    BaseDIDResolver,
    DIDMethodNotSupported,
    DIDNotFound,
    ResolutionMetadata,
    ResolutionResult,
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


@pytest_asyncio.fixture
async def profile():
    profile = await create_test_profile()
    yield profile


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
    assert isinstance(result.document_metadata, dict)


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


@pytest.mark.asyncio
async def test_resolve_with_metadata_extracts_document_metadata(profile):
    """Test that document_metadata is extracted from resolver response."""
    # Create a mock document with document_metadata embedded
    mock_doc = {
        "@context": "https://www.w3.org/ns/did/v1",
        "id": "did:test:123",
        "verificationMethod": [],
        "document_metadata": {
            "created": "2024-01-01T00:00:00Z",
            "updated": "2024-01-02T00:00:00Z",
            "versionId": "1",
        },
    }

    mock_resolver = MockResolver(["test"], resolved=mock_doc)
    test_resolver = DIDResolver([mock_resolver])

    result = await test_resolver.resolve_with_metadata(profile, "did:test:123")

    # Verify document_metadata was extracted
    assert result.document_metadata == {
        "created": "2024-01-01T00:00:00Z",
        "updated": "2024-01-02T00:00:00Z",
        "versionId": "1",
    }
    # Verify document_metadata was removed from did_document
    assert "document_metadata" not in result.did_document
    # Verify the document still has its other fields
    assert result.did_document["id"] == "did:test:123"


@pytest.mark.asyncio
async def test_resolve_with_metadata_no_document_metadata(profile):
    """Test that empty document_metadata is returned when not present."""
    mock_doc = {
        "@context": "https://www.w3.org/ns/did/v1",
        "id": "did:test:456",
        "verificationMethod": [],
    }

    mock_resolver = MockResolver(["test"], resolved=mock_doc)
    test_resolver = DIDResolver([mock_resolver])

    result = await test_resolver.resolve_with_metadata(profile, "did:test:456")

    # Verify empty document_metadata is returned
    assert result.document_metadata == {}
    # Verify did_document is unchanged
    assert result.did_document == mock_doc


def test_resolution_result_serialize_with_document_metadata():
    """Test that ResolutionResult.serialize() includes document_metadata."""
    did_doc = {"id": "did:test:789", "verificationMethod": []}
    metadata = ResolutionMetadata(
        ResolverType.NATIVE, "TestResolver", "2024-01-01T00:00:00Z", 100
    )
    doc_metadata = {"created": "2024-01-01", "updated": "2024-01-02"}

    result = ResolutionResult(did_doc, metadata, doc_metadata)
    serialized = result.serialize()

    # Verify all three fields are in serialized output
    assert "did_document" in serialized
    assert "metadata" in serialized
    assert "document_metadata" in serialized

    # Verify document_metadata content
    assert serialized["document_metadata"] == doc_metadata

    # Verify did_document is preserved
    assert serialized["did_document"] == did_doc


@pytest.mark.asyncio
async def test_resolve_with_metadata_with_document_metadata(resolver, profile):
    """Test that resolve_with_metadata extracts document_metadata from response."""
    result = await resolver.resolve_with_metadata(profile, TEST_DID0)
    assert isinstance(result.document_metadata, dict)
    # Should be empty for most resolvers
    assert result.document_metadata == {}

    # Test with a resolver that returns document_metadata
    mock_doc_with_metadata = {
        "@context": "test",
        "id": TEST_DID0,
        "document_metadata": {"created": "2024-01-01"},
    }
    resolver_with_meta = MockResolver(["test"], resolved=mock_doc_with_metadata)

    test_resolver = DIDResolver([resolver_with_meta])
    result_with_meta = await test_resolver.resolve_with_metadata(profile, "did:test:test")

    # document_metadata should have been extracted
    assert isinstance(result_with_meta.document_metadata, dict)
    # The document should not contain document_metadata anymore
    assert "document_metadata" not in result_with_meta.did_document


@pytest.mark.asyncio
async def test_resolver_caching_with_document_metadata(profile):
    """Test that resolver caches results including document_metadata."""
    # Create a resolver that returns document_metadata
    mock_doc_with_metadata = {
        "@context": "test",
        "id": TEST_DID0,
        "document_metadata": {"cached": True},
    }
    resolver_with_meta = MockResolver(["test"], resolved=mock_doc_with_metadata)

    test_resolver = DIDResolver([resolver_with_meta])

    # First call - should cache
    result1 = await test_resolver.resolve_with_metadata(profile, "did:test:test")

    # Second call - should use cache
    result2 = await test_resolver.resolve_with_metadata(profile, "did:test:test")

    # Both should have document_metadata
    assert isinstance(result1.document_metadata, dict)
    assert isinstance(result2.document_metadata, dict)
