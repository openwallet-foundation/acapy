from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ...wallet.base import BaseWallet

from .. import wallet as test_module
from ..injection_context import InjectionContext

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"


class TestWallet(AsyncTestCase):
    async def test_wallet_config_existing_replace(self):
        settings = {
            "wallet.seed": "00000000000000000000000000000000",
            "wallet.replace_public_did": True,
            "debug.enabled": True,
        }
        mock_wallet = async_mock.MagicMock(
            type="indy",
            name="Test Wallet",
            created=False,
            get_public_did=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(did=TEST_DID, verkey=TEST_VERKEY)
            ),
            set_public_did=async_mock.CoroutineMock(),
            create_local_did=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(did=TEST_DID, verkey=TEST_VERKEY)
            ),
        )
        context = InjectionContext(settings=settings, enforce_typing=False)
        context.injector.bind_instance(BaseWallet, mock_wallet)

        with async_mock.patch.object(
            test_module, "seed_to_did", async_mock.MagicMock()
        ) as mock_seed_to_did:
            mock_seed_to_did.return_value = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

            await test_module.wallet_config(context, provision=True)

    async def test_wallet_config_bad_seed_x(self):
        settings = {
            "wallet.seed": "00000000000000000000000000000000",
        }
        mock_wallet = async_mock.MagicMock(
            type="indy",
            name="Test Wallet",
            created=False,
            get_public_did=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(did=TEST_DID, verkey=TEST_VERKEY)
            ),
        )
        context = InjectionContext(settings=settings, enforce_typing=False)
        context.injector.bind_instance(BaseWallet, mock_wallet)

        with async_mock.patch.object(
            test_module, "seed_to_did", async_mock.MagicMock()
        ) as mock_seed_to_did:
            mock_seed_to_did.return_value = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

            with self.assertRaises(test_module.ConfigError):
                await test_module.wallet_config(context, provision=True)

    async def test_wallet_config_seed_local(self):
        settings = {
            "wallet.seed": "00000000000000000000000000000000",
            "wallet.local_did": True,
        }
        mock_wallet = async_mock.MagicMock(
            type="indy",
            name="Test Wallet",
            created=False,
            get_public_did=async_mock.CoroutineMock(return_value=None),
            set_public_did=async_mock.CoroutineMock(),
            create_local_did=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(did=TEST_DID, verkey=TEST_VERKEY)
            ),
        )
        context = InjectionContext(settings=settings, enforce_typing=False)
        context.injector.bind_instance(BaseWallet, mock_wallet)

        with async_mock.patch.object(
            test_module, "seed_to_did", async_mock.MagicMock()
        ) as mock_seed_to_did:
            mock_seed_to_did.return_value = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

            await test_module.wallet_config(context, provision=True)

    async def test_wallet_config_seed_public(self):
        settings = {
            "wallet.seed": "00000000000000000000000000000000",
        }
        mock_wallet = async_mock.MagicMock(
            type="indy",
            name="Test Wallet",
            created=False,
            get_public_did=async_mock.CoroutineMock(return_value=None),
            set_public_did=async_mock.CoroutineMock(),
            create_public_did=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(did=TEST_DID, verkey=TEST_VERKEY)
            ),
        )
        context = InjectionContext(settings=settings, enforce_typing=False)
        context.injector.bind_instance(BaseWallet, mock_wallet)

        with async_mock.patch.object(
            test_module, "seed_to_did", async_mock.MagicMock()
        ) as mock_seed_to_did:
            mock_seed_to_did.return_value = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

            await test_module.wallet_config(context, provision=True)

    async def test_wallet_config_seed_no_public_did(self):
        settings = {}
        mock_wallet = async_mock.MagicMock(
            type="indy",
            name="Test Wallet",
            created=False,
            get_public_did=async_mock.CoroutineMock(return_value=None),
            set_public_did=async_mock.CoroutineMock(),
            create_public_did=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(did=TEST_DID, verkey=TEST_VERKEY)
            ),
        )
        context = InjectionContext(settings=settings, enforce_typing=False)
        context.injector.bind_instance(BaseWallet, mock_wallet)

        with async_mock.patch.object(
            test_module, "seed_to_did", async_mock.MagicMock()
        ) as mock_seed_to_did:
            mock_seed_to_did.return_value = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

            await test_module.wallet_config(context, provision=True)
