from unittest import TestCase

from aries_cloudagent.did.did_key import DIDKey

from aries_cloudagent.wallet.default_verification_key_strategy import (
    DefaultVerificationKeyStrategy,
)

TEST_DID_SOV = "did:sov:LjgpST2rjsoxYegQDRm7EL"
TEST_DID_KEY = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"


class TestDefaultVerificationKeyStrategy(TestCase):
    def test_with_did_sov(self):
        strategy = DefaultVerificationKeyStrategy()
        assert strategy.get_verkey_id_for_did(TEST_DID_SOV) == TEST_DID_SOV + "#key-1"

    def test_with_did_key(self):
        strategy = DefaultVerificationKeyStrategy()
        assert (
            strategy.get_verkey_id_for_did(TEST_DID_KEY)
            == DIDKey.from_did(TEST_DID_KEY).key_id
        )

    def test_unsupported_did_method(self):
        strategy = DefaultVerificationKeyStrategy()
        assert strategy.get_verkey_id_for_did("did:test:test") is None
