"""Test IndyDIDResolver."""

import pytest

from asynctest import mock as async_mock
from pydid.verification_method import VerificationMethod

from ....core.in_memory import InMemoryProfile
from ....core.profile import Profile
from ....ledger.base import BaseLedger
from ....ledger.error import LedgerError
from ....ledger.multiple_ledger.ledger_requests_executor import (
    IndyLedgerRequestsExecutor,
)
from ....messaging.valid import IndyDID
from ....multitenant.base import BaseMultitenantManager
from ....multitenant.manager import MultitenantManager

from ...base import DIDNotFound, ResolverError
from ..indy import IndyDIDResolver, _routing_keys_as_did_key_urls

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
    ledger.get_all_endpoints_for_did = async_mock.CoroutineMock(
        return_value={
            "endpoint": "https://github.com/",
            "profile": "https://example.com/profile",
        }
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
    async def test_resolve_with_accept(
        self, profile: Profile, resolver: IndyDIDResolver
    ):
        """Test resolve method."""
        assert await resolver.resolve(
            profile, TEST_DID0, ["didcomm/aip1", "didcomm/aip2;env=rfc19"]
        )

    @pytest.mark.asyncio
    async def test_resolve_multitenant(
        self, profile: Profile, resolver: IndyDIDResolver, ledger: BaseLedger
    ):
        """Test resolve method."""
        profile.context.injector.bind_instance(
            BaseMultitenantManager,
            async_mock.MagicMock(MultitenantManager, autospec=True),
        )
        with async_mock.patch.object(
            IndyLedgerRequestsExecutor,
            "get_ledger_for_identifier",
            async_mock.CoroutineMock(return_value=("test_ledger_id", ledger)),
        ):
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

    @pytest.mark.asyncio
    async def test_supports_updated_did_sov_rules(
        self, resolver: IndyDIDResolver, ledger: BaseLedger, profile: Profile
    ):
        """Test that new attrib structure is supported."""
        example = {
            "endpoint": "https://example.com/endpoint",
            "routingKeys": ["HQhjaj4mcaS3Xci27a9QhnBrNpS91VNFUU4TDrtMxa9j"],
            "types": ["DIDComm", "did-communication", "endpoint"],
            "profile": "https://example.com",
            "linked_domains": "https://example.com",
        }

        ledger.get_all_endpoints_for_did = async_mock.CoroutineMock(
            return_value=example
        )
        assert await resolver.resolve(profile, TEST_DID0)

    @pytest.mark.asyncio
    async def test_supports_updated_did_sov_rules_no_endpoint_url(
        self, resolver: IndyDIDResolver, ledger: BaseLedger, profile: Profile
    ):
        """Test that new attrib structure is supported."""
        example = {
            "routingKeys": ["a-routing-key"],
            "types": ["DIDComm", "did-communication", "endpoint"],
        }

        ledger.get_all_endpoints_for_did = async_mock.CoroutineMock(
            return_value=example
        )
        result = await resolver.resolve(profile, TEST_DID0)
        assert "service" not in result

    @pytest.mark.parametrize(
        "types, result",
        [
            (
                [],
                ["endpoint", "did-communication"],
            ),
            (
                ["did-communication"],
                ["did-communication"],
            ),
            (
                ["endpoint", "did-communication", "DIDComm", "other-endpoint-type"],
                ["endpoint", "did-communication"],
            ),
            (
                ["endpoint", "did-communication", "DIDComm"],
                ["endpoint", "did-communication", "DIDComm"],
            ),
        ],
    )
    def test_process_endpoint_types(self, resolver: IndyDIDResolver, types, result):
        assert resolver.process_endpoint_types(types) == result

    @pytest.mark.parametrize(
        "keys",
        [
            ["3YJCx3TqotDWFGv7JMR5erEvrmgu5y4FDqjR7sKWxgXn"],
            ["did:key:z6MkgzZFYHiH9RhyMmkoyvNvVwnvgLxkVrJbureLx9HXsuKA"],
            [
                "did:key:z6MkgzZFYHiH9RhyMmkoyvNvVwnvgLxkVrJbureLx9HXsuKA#z6MkgzZFYHiH9RhyMmkoyvNvVwnvgLxkVrJbureLx9HXsuKA"
            ],
        ],
    )
    def test_routing_keys_as_did_key_urls(self, keys):
        for key in _routing_keys_as_did_key_urls(keys):
            assert key.startswith("did:key:")
            assert "#" in key
