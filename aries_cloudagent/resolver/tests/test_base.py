"""Test Base DID Resolver methods."""

import pytest
from ..base import BaseDIDResolver, ResolverType, ResolvedDIDDoc


class ExampleDIDResolver(BaseDIDResolver):
    """Test DID Resolver."""

    def __init__(self):
        super().__init__()

    async def setup(self, session):
        pass

    @property
    def supported_methods(self):
        return ["test"]

    async def resolve(self, session, did: str) -> ResolvedDIDDoc:
        return ResolvedDIDDoc({"id": "did:example:123"})


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
