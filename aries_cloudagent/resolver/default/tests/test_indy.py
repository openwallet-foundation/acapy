"""Test IndyDIDResolver."""

import pytest

from asynctest import mock as async_mock

from ....core.in_memory import InMemoryProfile
from ....core.profile import Profile
from ....ledger.base import BaseLedger
from ....ledger.error import LedgerError
from ....ledger.multiple_ledger.ledger_requests_executor import (
    IndyLedgerRequestsExecutor,
)
from ....messaging.valid import IndyDID

from ...base import DIDNotFound, ResolverError
from .. import indy as test_module
from ..indy import IndyDIDResolver

# pylint: disable=W0621
TEST_DID0 = "did:sov:WgWxqztrNooG92RXvxSTWv"


@pytest.fixture
def resolver():
    """Resolver fixture."""
    yield IndyDIDResolver()


@pytest.fixture
def ledger():
    """Ledger fixture."""
    ledger = async_mock.MagicMock(spec=BaseLedger)
    ledger.get_endpoint_for_did = async_mock.CoroutineMock(
        return_value="https://github.com/"
    )
    ledger.get_key_for_did = async_mock.CoroutineMock(return_value="key")
    yield ledger


@pytest.fixture
def profile(ledger):
    """Profile fixture."""
    profile = InMemoryProfile.test_profile()
    profile.context.injector.bind_instance(
        IndyLedgerRequestsExecutor,
        async_mock.MagicMock(
            get_ledger_for_identifier=async_mock.CoroutineMock(
                return_value=(None, ledger)
            )
        ),
    )
    yield profile


class TestIndyResolver:
    @pytest.mark.asyncio
    async def test_supported_did_regex(self, profile, resolver: IndyDIDResolver):
        """Test the supported_did_regex."""
        assert resolver.supported_did_regex == IndyDID.PATTERN
        assert await resolver.supports(profile, TEST_DID0)

    @pytest.mark.asyncio
    async def test_resolve(self, profile: Profile, resolver: IndyDIDResolver):
        """Test resolve method."""
        assert await resolver.resolve(profile, TEST_DID0)

    @pytest.mark.asyncio
    async def test_resolve_x_no_ledger(
        self, profile: Profile, resolver: IndyDIDResolver
    ):
        """Test resolve method with no ledger."""
        profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.CoroutineMock(
                    return_value=(None, None)
                )
            ),
        )
        with pytest.raises(ResolverError):
            await resolver.resolve(profile, TEST_DID0)

    @pytest.mark.asyncio
    async def test_resolve_x_did_not_found(
        self, resolver: IndyDIDResolver, ledger: BaseLedger, profile: Profile
    ):
        """Test resolve method when no did is found."""
        ledger.get_key_for_did.side_effect = LedgerError
        with pytest.raises(DIDNotFound):
            await resolver.resolve(profile, TEST_DID0)
