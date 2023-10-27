from unittest import IsolatedAsyncioTestCase
from aries_cloudagent.tests import mock

from aries_cloudagent.wallet.key_type import ED25519

from .....core.in_memory import InMemoryProfile
from .....wallet.in_memory import InMemoryWallet
from ...error import LinkedDataProofException

from ..wallet_key_pair import WalletKeyPair


class TestWalletKeyPair(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = InMemoryProfile.test_profile()

    async def test_sign_x_no_public_key(self):
        key_pair = WalletKeyPair(profile=self.profile, key_type=ED25519)

        with self.assertRaises(LinkedDataProofException) as context:
            await key_pair.sign(b"Message")
        assert "No key to sign with" in str(context.exception)

    async def test_sign(self):
        public_key_base58 = "verkey"
        key_pair = WalletKeyPair(
            profile=self.profile,
            key_type=ED25519,
            public_key_base58=public_key_base58,
        )
        signed = mock.MagicMock()

        with mock.patch.object(
            InMemoryWallet,
            "sign_message",
            mock.CoroutineMock(return_value=signed),
        ) as sign_message:
            singed_ret = await key_pair.sign(b"Message")

            assert signed == singed_ret
            sign_message.assert_called_once_with(
                message=b"Message", from_verkey=public_key_base58
            )

    async def test_verify_x_no_public_key(self):
        key_pair = WalletKeyPair(profile=self.profile, key_type=ED25519)

        with self.assertRaises(LinkedDataProofException) as context:
            await key_pair.verify(b"Message", b"signature")
        assert "No key to verify with" in str(context.exception)

    async def test_verify(self):
        public_key_base58 = "verkey"
        key_pair = WalletKeyPair(
            profile=self.profile,
            key_type=ED25519,
            public_key_base58=public_key_base58,
        )

        with mock.patch.object(
            InMemoryWallet,
            "verify_message",
            mock.CoroutineMock(return_value=True),
        ) as verify_message:
            verified = await key_pair.verify(b"Message", b"signature")

            assert verified
            verify_message.assert_called_once_with(
                message=b"Message",
                signature=b"signature",
                from_verkey=public_key_base58,
                key_type=ED25519,
            )

    async def test_from_verification_method_x_no_public_key_base58(self):
        key_pair = WalletKeyPair(profile=self.profile, key_type=ED25519)

        with self.assertRaises(LinkedDataProofException) as context:
            key_pair.from_verification_method({})
        assert "no publicKeyBase58" in str(context.exception)
