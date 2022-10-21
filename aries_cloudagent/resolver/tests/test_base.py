"""Test Base DID Resolver methods."""

import pytest
import re

from asynctest import mock as async_mock
from pydid import DIDDocument

from ..base import BaseDIDResolver, DIDMethodNotSupported, ResolverType


class ExampleDIDResolver(BaseDIDResolver):
    """Test DID Resolver."""

    def __init__(self):
        super().__init__()

    async def setup(self, context):
        pass

    @property
    def supported_did_regex(self):
        return re.compile("^did:example:[a-zA-Z0-9_.-]+$")

    async def _resolve(self, profile, did, accept) -> DIDDocument:
        return DIDDocument("did:example:123")


@pytest.fixture
def native_resolver():
    resolver = ExampleDIDResolver()
    resolver.type = ResolverType.NATIVE
    yield resolver


@pytest.fixture
def non_native_resolver():
    yield ExampleDIDResolver()


@pytest.fixture
def profile():
    yield async_mock.MagicMock()


def test_native_on_native(native_resolver):
    assert native_resolver.native is True


def test_native_on_non_native(non_native_resolver):
    assert non_native_resolver.native is False


@pytest.mark.asyncio
async def test_supports(profile, native_resolver):
    assert not await native_resolver.supports(profile, "did:test:basdfasdfas")
    assert await native_resolver.supports(profile, "did:example:WgWxqztrNooG92RXvxSTWv")


@pytest.mark.asyncio
async def test_resolve_x(native_resolver):
    with pytest.raises(DIDMethodNotSupported) as x_did:
        await native_resolver.resolve(None, "did:nosuchmethod:xxx")
    assert "does not support DID method" in str(x_did.value)


@pytest.mark.asyncio
async def test_supported_methods():
    class TestDIDResolver(BaseDIDResolver):
        async def setup(self, context):
            pass

        @property
        def supported_methods(self):
            return ["example"]

        async def _resolve(self, profile, did, accept) -> DIDDocument:
            return DIDDocument("did:example:123")

    with pytest.deprecated_call():
        assert await TestDIDResolver().supports(
            profile, "did:example:WgWxqztrNooG92RXvxSTWv"
        )
