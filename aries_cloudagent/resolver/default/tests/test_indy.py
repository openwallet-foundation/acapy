"""Test IndyDIDResolver."""

import pytest
from asynctest import mock as async_mock

from ..indy import IndyDIDResolver
from ....core.in_memory import InMemoryProfile
from ....core.profile import Profile
from ....ledger.indy import IndySdkLedger
from ....ledger.error import LedgerError
from ...tests.test_did import TEST_DID0
from ...base import ResolverError, DIDNotFound

# pylint: disable=W0621


@pytest.fixture
def resolver():
    """Resolver fixture."""
    yield IndyDIDResolver()


@pytest.fixture
def ledger():
    """Ledger fixture."""
    ledger = async_mock.MagicMock()
    ledger.get_endpoint_for_did = async_mock.CoroutineMock(return_value="endpoint")
    ledger.get_key_for_did = async_mock.CoroutineMock(return_value="key")
    yield ledger


@pytest.fixture
def profile(ledger):
    """Profile fixture."""
    profile = InMemoryProfile.test_profile()
    profile.context.injector.bind_instance(IndySdkLedger, ledger)
    yield profile


def test_supported_methods(resolver: IndyDIDResolver):
    """Test the supported_methods."""
    assert resolver.supported_methods == ["sov"]
    assert resolver.supports("sov")


@pytest.mark.asyncio
async def test_resolve(resolver: IndyDIDResolver, profile: Profile):
    """Test resolve method."""
    assert await resolver.resolve(profile, TEST_DID0)


@pytest.mark.asyncio
async def test_resolve_x_no_ledger(resolver: IndyDIDResolver, profile: Profile):
    """Test resolve method with no ledger."""
    profile.context.injector.clear_binding(IndySdkLedger)
    with pytest.raises(ResolverError):
        await resolver.resolve(profile, TEST_DID0)


@pytest.mark.asyncio
async def test_resolve_x_did_not_found(
    resolver: IndyDIDResolver, ledger: IndySdkLedger, profile: Profile
):
    """Test resolve method when no did is found."""
    ledger.get_key_for_did.side_effect = LedgerError
    with pytest.raises(DIDNotFound):
        await resolver.resolve(profile, TEST_DID0)
