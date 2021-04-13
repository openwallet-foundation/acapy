"""Test Base DID Resolver methods."""

import pytest

from pydid import DIDDocument

from ..base import BaseDIDResolver, DIDMethodNotSupported, ResolverType


class ExampleDIDResolver(BaseDIDResolver):
    """Test DID Resolver."""

    def __init__(self):
        super().__init__()

    async def setup(self, context):
        pass

    @property
    def supported_methods(self):
        return ["test"]

    async def _resolve(self, profile, did) -> DIDDocument:
        return DIDDocument("did:example:123")


@pytest.fixture
def native_resolver():
    resolver = ExampleDIDResolver()
    resolver.type = ResolverType.NATIVE
    yield resolver


@pytest.fixture
def non_native_resolver():
    yield ExampleDIDResolver()


def test_native_on_native(native_resolver):
    assert native_resolver.native is True


def test_native_on_non_native(non_native_resolver):
    assert non_native_resolver.native is False


def test_supports(native_resolver):
    assert native_resolver.supports("test") is True
    assert native_resolver.supports("not supported") is False


@pytest.mark.asyncio
async def test_resolve_x(native_resolver):
    with pytest.raises(DIDMethodNotSupported) as x_did:
        await native_resolver.resolve(None, "did:nosuchmethod:xxx")
    assert "does not support DID method" in str(x_did.value)
