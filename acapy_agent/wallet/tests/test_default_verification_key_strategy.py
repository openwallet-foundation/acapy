from unittest import IsolatedAsyncioTestCase
import pytest

from acapy_agent.resolver.did_resolver import DIDResolver

from ...did.did_key import DIDKey
from ...utils.testing import create_test_profile
from ...wallet.default_verification_key_strategy import (
    DefaultVerificationKeyStrategy,
)

TEST_DID_SOV = "did:sov:LjgpST2rjsoxYegQDRm7EL"
TEST_DID_KEY = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"


class TestDefaultVerificationKeyStrategy(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.profile = await create_test_profile()
        resolver = DIDResolver()
        self.profile.context.injector.bind_instance(DIDResolver, resolver)

    async def test_with_did_sov(self):
        strategy = DefaultVerificationKeyStrategy()
        assert (
            await strategy.get_verification_method_id_for_did(TEST_DID_SOV, self.profile)
            == TEST_DID_SOV + "#key-1"
        )

    async def test_with_did_key(self):
        strategy = DefaultVerificationKeyStrategy()
        assert (
            await strategy.get_verification_method_id_for_did(TEST_DID_KEY, self.profile)
            == DIDKey.from_did(TEST_DID_KEY).key_id
        )

    async def test_unsupported_did_method(self):
        strategy = DefaultVerificationKeyStrategy()
        with pytest.raises(Exception):
            await strategy.get_verification_method_id_for_did(
                "did:test:test", self.profile
            )
