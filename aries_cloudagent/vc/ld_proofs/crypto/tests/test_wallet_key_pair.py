from asynctest import TestCase, mock as async_mock

from aries_cloudagent.wallet.key_type import ED25519

from .....wallet.key_pair import KeyType

from ...error import LinkedDataProofException

from ..wallet_key_pair import WalletKeyPair


class TestWalletKeyPair(TestCase):
    async def setUp(self):
        self.wallet = async_mock.MagicMock()

    async def test_sign_x_no_public_key(self):
        key_pair = WalletKeyPair(wallet=self.wallet, key_type=ED25519)

        with self.assertRaises(LinkedDataProofException) as context:
            await key_pair.sign(b"Message")
        assert "No key to sign with" in str(context.exception)

    async def test_sign(self):
        public_key_base58 = "verkey"
        key_pair = WalletKeyPair(
            wallet=self.wallet,
            key_type=ED25519,
            public_key_base58=public_key_base58,
        )
        signed = async_mock.MagicMock()

        self.wallet.sign_message = async_mock.CoroutineMock(return_value=signed)

        singed_ret = await key_pair.sign(b"Message")

        assert signed == singed_ret
        self.wallet.sign_message.assert_called_once_with(
            message=b"Message", from_verkey=public_key_base58
        )

    async def test_verify_x_no_public_key(self):
        key_pair = WalletKeyPair(wallet=self.wallet, key_type=ED25519)

        with self.assertRaises(LinkedDataProofException) as context:
            await key_pair.verify(b"Message", b"signature")
        assert "No key to verify with" in str(context.exception)

    async def test_verify(self):
        public_key_base58 = "verkey"
        key_pair = WalletKeyPair(
            wallet=self.wallet,
            key_type=ED25519,
            public_key_base58=public_key_base58,
        )
        self.wallet.verify_message = async_mock.CoroutineMock(return_value=True)

        verified = await key_pair.verify(b"Message", b"signature")

        assert verified
        self.wallet.verify_message.assert_called_once_with(
            message=b"Message",
            signature=b"signature",
            from_verkey=public_key_base58,
            key_type=ED25519,
        )

    async def test_from_verification_method_x_no_public_key_base58(self):
        key_pair = WalletKeyPair(wallet=self.wallet, key_type=ED25519)

        with self.assertRaises(LinkedDataProofException) as context:
            key_pair.from_verification_method({})
        assert "no publicKeyBase58" in str(context.exception)
