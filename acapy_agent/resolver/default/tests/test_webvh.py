from unittest import mock

import pytest
import pytest_asyncio
from did_webvh.resolver import ResolutionResult as WebvhResolutionResult

from ....core.profile import Profile
from ....messaging.valid import DIDWebvh
from ....utils.testing import create_test_profile
from ..webvh import WebvhDIDResolver

TEST_DID = "did:webvh:Qma6mc1qZw3NqxwX6SB5GPQYzP4pGN2nXD15Jwi4bcDBKu:domain.example"


@pytest.fixture
def resolver():
    """Resolver fixture."""
    yield WebvhDIDResolver()


@pytest_asyncio.fixture
async def profile():
    """Profile fixture."""
    yield await create_test_profile()


@pytest.mark.asyncio
async def test_supported_did_regex(profile, resolver: WebvhDIDResolver):
    """Test the supported_did_regex."""
    assert resolver.supported_did_regex == DIDWebvh.PATTERN
    assert await resolver.supports(
        profile,
        TEST_DID,
    )


@pytest.mark.asyncio
async def test_resolve(resolver: WebvhDIDResolver, profile: Profile):
    """Test resolve method."""
    assert await resolver.resolve(profile, TEST_DID)


@pytest.mark.asyncio
async def test_resolve_with_document_metadata(
    resolver: WebvhDIDResolver, profile: Profile
):
    """Test that resolve includes document_metadata when returned by did_webvh."""
    # Mock the resolve_did to return a result with document_metadata
    mock_doc = {"id": TEST_DID, "verificationMethod": []}
    mock_doc_metadata = {"created": "2024-01-01", "updated": "2024-01-02"}
    mock_result = mock.Mock(spec=WebvhResolutionResult)
    mock_result.document = mock_doc
    mock_result.document_metadata = mock_doc_metadata
    mock_result.resolution_metadata = {}

    with mock.patch(
        "acapy_agent.resolver.default.webvh.resolve_did", return_value=mock_result
    ):
        result = await resolver._resolve(profile, TEST_DID)

        # Verify document_metadata was included in the result
        assert "document_metadata" in result
        assert result["document_metadata"] == mock_doc_metadata


@pytest.mark.asyncio
async def test_resolve_without_document_metadata(
    resolver: WebvhDIDResolver, profile: Profile
):
    """Test that resolve works when document_metadata is not returned."""
    # Mock the resolve_did to return a result without document_metadata
    mock_doc = {"id": TEST_DID, "verificationMethod": []}
    mock_result = mock.Mock(spec=WebvhResolutionResult)
    mock_result.document = mock_doc
    mock_result.document_metadata = None  # No document_metadata
    mock_result.resolution_metadata = {}

    with mock.patch(
        "acapy_agent.resolver.default.webvh.resolve_did", return_value=mock_result
    ):
        result = await resolver._resolve(profile, TEST_DID)

        # Verify document_metadata was not added when not present
        assert "document_metadata" not in result
        assert result == mock_doc


@pytest.mark.asyncio
async def test_resolve_with_empty_document_metadata(
    resolver: WebvhDIDResolver, profile: Profile
):
    """Test that resolve handles empty document_metadata dict."""
    # Mock the resolve_did to return a result with empty document_metadata
    mock_doc = {"id": TEST_DID, "verificationMethod": []}
    mock_result = mock.Mock(spec=WebvhResolutionResult)
    mock_result.document = mock_doc
    mock_result.document_metadata = {}  # Empty dict is truthy but empty
    mock_result.resolution_metadata = {}

    with mock.patch(
        "acapy_agent.resolver.default.webvh.resolve_did", return_value=mock_result
    ):
        result = await resolver._resolve(profile, TEST_DID)

        # Empty dict {} is falsy in Python boolean context, so it won't be added
        assert "document_metadata" not in result
