"""Test DIDWebRegistry."""

import pytest
import re
from ..registry import DIDWebRegistry

DID_WEB = re.compile(
    r"^did:web:[a-z0-9]+(?:\.[a-z0-9]+)*(?::\d+)?(?:\/[^#\s]*)?(?:#.*)?\s*$"
)


TEST_WED_DID_0 = "did:web:example.com/anoncreds/v0/SCHEMA/asdf"
TEST_WED_DID_1 = "did:web:example.com"
TEST_WED_DID_2 = "did:web:sub.example.com"
TEST_WED_DID_3 = "did:web:example.com:8080"
TEST_WED_DID_4 = "did:web:sub.example.com/path/to/resource"
TEST_WED_DID_5 = "did:web:example.com/path/to/resource#fragment"


@pytest.fixture
def registry():
    """Registry fixture"""
    yield DIDWebRegistry()


class TestLegacyIndyRegistry:
    @pytest.mark.asyncio
    async def test_supported_did_regex(self, registry: DIDWebRegistry):
        """Test the supported_did_regex."""

        assert registry.supported_identifiers_regex == DID_WEB
        assert bool(registry.supported_identifiers_regex.match(TEST_WED_DID_0))
        assert bool(registry.supported_identifiers_regex.match(TEST_WED_DID_1))
        assert bool(registry.supported_identifiers_regex.match(TEST_WED_DID_2))
        assert bool(registry.supported_identifiers_regex.match(TEST_WED_DID_3))
        assert bool(registry.supported_identifiers_regex.match(TEST_WED_DID_4))
        assert bool(registry.supported_identifiers_regex.match(TEST_WED_DID_5))
