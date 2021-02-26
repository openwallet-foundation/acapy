"""Test universal resolver with http bindings."""

from typing import Dict, Union

import pytest
from asynctest import mock as async_mock

from ....connections.models.diddoc_v2 import DIDDoc
from ...base import DIDNotFound, ResolverError
from .. import http_universal as test_module
from ..http_universal import HTTPUniversalDIDResolver

# pylint: disable=redefined-outer-name


@pytest.fixture
def resolver():
    """Resolver fixture."""
    uni_resolver = HTTPUniversalDIDResolver()
    uni_resolver.configure(
        {
            "endpoint": "https://dev.uniresolver.io/1.0/identifiers",
            "methods": [
                "sov",
                "abt",
                "btcr",
                "erc725",
                "dom",
                "stack",
                "ethr",
                "web",
                "v1",
                "key",
                "ipid",
                "jolo",
                "hacera",
                "elem",
                "seraphid",
                "github",
                "ccp",
                "work",
                "ont",
                "kilt",
                "evan",
                "echo",
                "factom",
                "dock",
                "trust",
                "io",
                "bba",
                "bid",
                "schema",
                "ion",
                "ace",
                "gatc",
                "unisot",
                "icon",
            ],
        }
    )
    yield uni_resolver


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
        200, {"didDocument": {"id": "did:example:123"}}
    )
    doc: DIDDoc = await resolver.resolve(
        profile, "did:sov:WRfXPg8dantKVubE3HX8pw"
    )
    assert doc.id == "did:example:123"


@pytest.mark.asyncio
async def test_resolve_not_found(profile, resolver, mock_client_session):
    mock_client_session.response = MockResponse(404, "Not found")
    with pytest.raises(DIDNotFound):
        await resolver.resolve(profile, "did:sov:1234567")


@pytest.mark.asyncio
async def test_resolve_unexpeceted_status(profile, resolver, mock_client_session):
    mock_client_session.response = MockResponse(
        500, "Server failed to complete request"
    )
    with pytest.raises(ResolverError):
        await resolver.resolve(profile, "did:sov:123")
