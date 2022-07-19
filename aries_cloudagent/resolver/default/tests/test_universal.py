"""Test universal resolver with http bindings."""

import re
from typing import Dict, Union

import pytest
from asynctest import mock as async_mock

from aries_cloudagent.resolver.base import DIDNotFound, ResolverError
from .. import universal as test_module
from ..universal import UniversalResolver


@pytest.fixture
async def resolver():
    """Resolver fixture."""
    yield UniversalResolver(
        endpoint="https://example.com", supported_did_regex=re.compile("^did:sov:.*$")
    )


@pytest.fixture
def profile():
    """Profile fixture."""
    yield async_mock.MagicMock()


class MockResponse:
    """Mock http response."""

    def __init__(self, status: int, body: Union[str, Dict]):
        self.status = status
        self.body = body

    async def json(self):
        return self.body

    async def text(self):
        return self.body

    async def __aenter__(self):
        """For use as async context."""
        return self

    async def __aexit__(self, err_type, err_value, err_exc):
        """For use as async context."""


class MockClientSession:
    """Mock client session."""

    def __init__(self, response: MockResponse = None):
        self.response = response

    def __call__(self):
        return self

    async def __aenter__(self):
        """For use as async context."""
        return self

    async def __aexit__(self, err_type, err_value, err_exc):
        """For use as async context."""

    def get(self, endpoint):
        """Return response."""
        return self.response


@pytest.fixture
def mock_client_session():
    temp = test_module.aiohttp.ClientSession
    session = MockClientSession()
    test_module.aiohttp.ClientSession = session
    yield session
    test_module.aiohttp.ClientSession = temp


@pytest.mark.asyncio
async def test_resolve(profile, resolver, mock_client_session):
    mock_client_session.response = MockResponse(
        200,
        {
            "didDocument": {
                "id": "did:example:123",
                "@context": "https://www.w3.org/ns/did/v1",
            }
        },
    )
    doc = await resolver.resolve(profile, "did:sov:WRfXPg8dantKVubE3HX8pw")
    assert doc.get("id") == "did:example:123"


@pytest.mark.asyncio
async def test_resolve_not_found(profile, resolver, mock_client_session):
    mock_client_session.response = MockResponse(404, "Not found")
    with pytest.raises(DIDNotFound):
        await resolver.resolve(profile, "did:sov:WRfXPg8dantKVubE3HX8pw")


@pytest.mark.asyncio
async def test_resolve_unexpeceted_status(profile, resolver, mock_client_session):
    mock_client_session.response = MockResponse(
        500, "Server failed to complete request"
    )
    with pytest.raises(ResolverError):
        await resolver.resolve(profile, "did:sov:WRfXPg8dantKVubE3HX8pw")
