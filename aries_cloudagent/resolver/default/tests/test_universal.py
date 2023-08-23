"""Test universal resolver with http bindings."""

import re
from typing import Dict, Union

from asynctest import mock as async_mock
import pytest

from ....config.settings import Settings
from ....core.in_memory import InMemoryProfile

from .. import universal as test_module
from ...base import DIDNotFound, ResolverError
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
    yield InMemoryProfile.test_profile()


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

    def __call__(self, headers):
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
async def test_resolve_unexpected_status(profile, resolver, mock_client_session):
    mock_client_session.response = MockResponse(
        500, "Server failed to complete request"
    )
    with pytest.raises(ResolverError):
        await resolver.resolve(profile, "did:sov:WRfXPg8dantKVubE3HX8pw")


@pytest.mark.asyncio
async def test_fetch_resolver_props(mock_client_session: MockClientSession):
    mock_client_session.response = MockResponse(200, {"test": "json"})
    assert await UniversalResolver()._fetch_resolver_props() == {"test": "json"}
    mock_client_session.response = MockResponse(404, "Not found")
    with pytest.raises(ResolverError):
        await UniversalResolver()._fetch_resolver_props()


@pytest.mark.asyncio
async def test_get_supported_did_regex():
    props = {"example": {"http": {"pattern": "match a test string"}}}
    with async_mock.patch.object(
        UniversalResolver,
        "_fetch_resolver_props",
        async_mock.CoroutineMock(return_value=props),
    ):
        pattern = await UniversalResolver()._get_supported_did_regex()
        assert pattern.fullmatch("match a test string")


def test_compile_supported_did_regex():
    patterns = ["one", "two", "three"]
    compiled = test_module._compile_supported_did_regex(patterns)
    assert compiled.match("one")
    assert compiled.match("two")
    assert compiled.match("three")


@pytest.mark.asyncio
async def test_setup_endpoint_regex_set(resolver: UniversalResolver):
    settings = Settings(
        {
            "resolver.universal": "http://example.com",
            "resolver.universal.supported": "test",
        }
    )
    context = async_mock.MagicMock()
    context.settings = settings
    with async_mock.patch.object(
        test_module,
        "_compile_supported_did_regex",
        async_mock.MagicMock(return_value="pattern"),
    ):
        await resolver.setup(context)

    assert resolver._endpoint == "http://example.com"
    assert resolver._supported_did_regex == "pattern"


@pytest.mark.asyncio
async def test_setup_endpoint_set(resolver: UniversalResolver):
    settings = Settings(
        {
            "resolver.universal": "http://example.com",
        }
    )
    context = async_mock.MagicMock()
    context.settings = settings
    with async_mock.patch.object(
        UniversalResolver,
        "_get_supported_did_regex",
        async_mock.CoroutineMock(return_value="pattern"),
    ):
        await resolver.setup(context)

    assert resolver._endpoint == "http://example.com"
    assert resolver._supported_did_regex == "pattern"


@pytest.mark.asyncio
async def test_setup_endpoint_default(resolver: UniversalResolver):
    settings = Settings(
        {
            "resolver.universal": "DEFAULT",
        }
    )
    context = async_mock.MagicMock()
    context.settings = settings
    with async_mock.patch.object(
        UniversalResolver,
        "_get_supported_did_regex",
        async_mock.CoroutineMock(return_value="pattern"),
    ):
        await resolver.setup(context)

    assert resolver._endpoint == test_module.DEFAULT_ENDPOINT
    assert resolver._supported_did_regex == "pattern"


@pytest.mark.asyncio
async def test_setup_endpoint_unset(resolver: UniversalResolver):
    settings = Settings()
    context = async_mock.MagicMock()
    context.settings = settings
    with async_mock.patch.object(
        UniversalResolver,
        "_get_supported_did_regex",
        async_mock.CoroutineMock(return_value="pattern"),
    ):
        await resolver.setup(context)

    assert resolver._endpoint == test_module.DEFAULT_ENDPOINT
    assert resolver._supported_did_regex == "pattern"


@pytest.mark.asyncio
async def test_supported_did_regex_not_setup():
    resolver = UniversalResolver()
    with pytest.raises(ResolverError):
        resolver.supported_did_regex
