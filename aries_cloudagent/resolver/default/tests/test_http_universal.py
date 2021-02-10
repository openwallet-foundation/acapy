"""Test universal resolver with http bindings."""

import pytest
from asynctest import mock as async_mock

from ..http_universal import HTTPUniversalDIDResolver


@pytest.fixture
def resolver():
    uni_resolver = HTTPUniversalDIDResolver()
    uni_resolver.configure({
        "endpoint": "https://dev.uniresolver.io/1.0/identifiers",
        "methods": [
            "sov", "abt", "btcr", "erc725", "dom", "stack", "ethr", "web", "v1",
            "key", "ipid", "jolo", "hacera", "elem", "seraphid", "github",
            "ccp", "work", "ont", "kilt", "evan", "echo", "factom", "dock",
            "trust", "io", "bba", "bid", "schema", "ion", "ace", "gatc",
            "unisot", "icon"
        ]
    })
    yield uni_resolver


@pytest.fixture
def profile():
    yield async_mock.MagicMock()


@pytest.mark.asyncio
async def test_resolve(resolver, profile):
    print((await resolver.resolve(profile, "did:sov:WRfXPg8dantKVubE3HX8pw")).serialize())
