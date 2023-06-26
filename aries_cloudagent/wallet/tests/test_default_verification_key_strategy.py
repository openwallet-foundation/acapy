from unittest import TestCase

from aries_cloudagent.core.profile import Profile

from aries_cloudagent.did.did_key import DIDKey

from aries_cloudagent.wallet.default_verification_key_strategy import (
    DefaultVerificationKeyStrategy,
)

TEST_DID_SOV = "did:sov:LjgpST2rjsoxYegQDRm7EL"
TEST_DID_KEY = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"


class TestDefaultVerificationKeyStrategy(TestCase):
    async def test_with_did_sov(self):
        strategy = DefaultVerificationKeyStrategy()
        assert (
            await strategy.get_verification_method_id_for_did(TEST_DID_SOV, Profile())
            == TEST_DID_SOV + "#key-1"
        )

    async def test_with_did_key(self):
        strategy = DefaultVerificationKeyStrategy()
        assert (
            await strategy.get_verification_method_id_for_did(TEST_DID_KEY, Profile())
            == DIDKey.from_did(TEST_DID_KEY).key_id
        )

    async def test_unsupported_did_method(self):
        strategy = DefaultVerificationKeyStrategy()
        assert (
            await strategy.get_verification_method_id_for_did(
                "did:test:test", Profile()
            )
            is None
        )
