"""Test universal resolver with http bindings."""

import re
from typing import Dict, Optional, Union

import pytest

from ....config.settings import Settings
from ....tests import mock
from ....utils.testing import create_test_profile
from ...base import DIDNotFound, ResolverError
from .. import universal as test_module
from ..universal import UniversalResolver


@pytest.fixture
async def resolver():
    """Resolver fixture."""
    yield UniversalResolver(
        endpoint="https://example.com", supported_did_regex=re.compile("^did:sov:.*$")
    )


@pytest.fixture
async def profile():
    """Profile fixture."""
    profile = await create_test_profile()
    yield profile


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

    def __init__(self, response: Optional[MockResponse] = None):
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
    mock_client_session.response = MockResponse(500, "Server failed to complete request")
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
    # Old response format
    props = {"example": {"http": {"pattern": "match a test string"}}}
    with mock.patch.object(
        UniversalResolver,
        "_fetch_resolver_props",
        mock.CoroutineMock(return_value=props),
    ):
        pattern = await UniversalResolver()._get_supported_did_regex()
        assert pattern.fullmatch("match a test string")

    # Example response from dev universal resolver 1.0
    props = {
        "^(did:sov:(?:(?:\\w[-\\w]*(?::\\w[-\\w]*)*):)?(?:[1-9A-HJ-NP-Za-km-z]{21,22}))$": {
            "libIndyPath": "",
            "openParallel": "false",
            "poolVersions": "_;2;test;2;builder;2;danube;2;idunion;2;idunion:test;2;indicio;2;indicio:test;2;indicio:demo;2;nxd;2;findy:test;2;bcovrin;2;bcovrin:test;2;bcovrin:dev;2;candy;2;candy:test;2;candy:dev;2",
            "submitterDidSeeds": "_;_;test;_;builder;_;danube;_;idunion;_;idunion:test;_;indicio;_;indicio:test;_;indicio:demo;_;nxd;_;findy:test;_;bcovrin;_;bcovrin:test;_;bcovrin:dev;_;candy;_;candy:test;_;candy:dev;_",
            "http": {
                "resolveUri": "http://driver-did-sov:8080/1.0/identifiers/",
                "propertiesUri": "http://driver-did-sov:8080/1.0/properties",
            },
            "walletNames": "_;w1;test;w2;builder;w3;danube;w4;idunion;w5;idunion:test;w6;indicio;w7;indicio:test;w8;indicio:demo;w9;nxd;w11;findy:test;w12;bcovrin;w13;bcovrin:test;w14;bcovrin:dev;w15;candy;w16;candy:test;w17;candy:dev;w18",
            "poolConfigs": "_;./sovrin/_.txn;test;./sovrin/test.txn;builder;./sovrin/builder.txn;danube;./sovrin/danube.txn;idunion;./sovrin/idunion.txn;idunion:test;./sovrin/idunion-test.txn;indicio;./sovrin/indicio.txn;indicio:test;./sovrin/indicio-test.txn;indicio:demo;./sovrin/indicio-demo.txn;nxd;./sovrin/nxd.txn;bcovrin:test;./sovrin/bcovrin-test.txn;candy;./sovrin/candy.txn;candy:test;./sovrin/candy-test.txn;candy:dev;./sovrin/candy-dev.txn",
        }
    }
    with mock.patch.object(
        UniversalResolver,
        "_fetch_resolver_props",
        mock.CoroutineMock(return_value=props),
    ):
        pattern = await UniversalResolver()._get_supported_did_regex()
        assert pattern.match("did:sov:WRfXPg8dantKVubE3HX8pw")


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
    context = mock.MagicMock()
    context.settings = settings
    with mock.patch.object(
        test_module,
        "_compile_supported_did_regex",
        mock.MagicMock(return_value="pattern"),
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
    context = mock.MagicMock()
    context.settings = settings
    with mock.patch.object(
        UniversalResolver,
        "_get_supported_did_regex",
        mock.CoroutineMock(return_value="pattern"),
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
    context = mock.MagicMock()
    context.settings = settings
    with mock.patch.object(
        UniversalResolver,
        "_get_supported_did_regex",
        mock.CoroutineMock(return_value="pattern"),
    ):
        await resolver.setup(context)

    assert resolver._endpoint == test_module.DEFAULT_ENDPOINT
    assert resolver._supported_did_regex == "pattern"


@pytest.mark.asyncio
async def test_setup_endpoint_unset(resolver: UniversalResolver):
    settings = Settings()
    context = mock.MagicMock()
    context.settings = settings
    with mock.patch.object(
        UniversalResolver,
        "_get_supported_did_regex",
        mock.CoroutineMock(return_value="pattern"),
    ):
        await resolver.setup(context)

    assert resolver._endpoint == test_module.DEFAULT_ENDPOINT
    assert resolver._supported_did_regex == "pattern"


@pytest.mark.asyncio
async def test_supported_did_regex_not_setup():
    resolver = UniversalResolver()
    with pytest.raises(ResolverError):
        resolver.supported_did_regex
