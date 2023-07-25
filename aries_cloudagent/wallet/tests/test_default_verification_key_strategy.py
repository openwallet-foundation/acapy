from asynctest import mock
from unittest import TestCase

from aries_cloudagent.core.profile import Profile

from aries_cloudagent.did.did_key import DIDKey

from aries_cloudagent.wallet.did_info import DIDInfo
from aries_cloudagent.wallet.default_verification_key_strategy import (
    DefaultVerificationKeyStrategy,
)
from aries_cloudagent.wallet.in_memory import InMemoryWallet

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

    async def test_verification_key_for_did_with_sov(self):
        strategy = DefaultVerificationKeyStrategy()

        with mock.patch.object(
            InMemoryWallet,
            "get_local_did",
            mock.CoroutineMock(return_value=mock.MagicMock(DIDInfo)),
        ) as mock_get_local_did:
            verification_key = await strategy.get_verification_key_for_did(TEST_DID_SOV)
            assert verification_key == mock_get_local_did

            mock_get_local_did.assert_called_once_with("LjgpST2rjsoxYegQDRm7EL")

    async def test_verification_key_for_did_with_key(self):
        strategy = DefaultVerificationKeyStrategy()

        with mock.patch.object(
            InMemoryWallet,
            "get_local_did",
            mock.CoroutineMock(return_value=mock.MagicMock(DIDInfo)),
        ) as mock_get_local_did:
            verification_key = await strategy.get_verification_key_for_did(TEST_DID_KEY)
            assert verification_key == mock_get_local_did

            mock_get_local_did.assert_called_once_with(TEST_DID_KEY)
