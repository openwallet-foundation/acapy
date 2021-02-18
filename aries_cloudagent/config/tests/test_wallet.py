from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ...core.profile import Profile, ProfileManager, ProfileSession
from ...wallet.base import BaseWallet

from .. import wallet as test_module
from ..injector import Injector
from ..injection_context import InjectionContext

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"


class MockManager(ProfileManager):
    def __init__(self, profile):
        self.profile = profile
        self.calls = []

    async def provision(self, context, config):
        self.calls.append(("provision", context, config))
        return self.profile

    async def open(self, context, config):
        self.calls.append(("open", context, config))
        return self.profile


class TestWalletConfig(AsyncTestCase):
    async def setUp(self):
        self.injector = Injector(enforce_typing=False)
        self.session = async_mock.MagicMock(ProfileSession)()
        self.session.commit = async_mock.CoroutineMock()
        self.profile = async_mock.MagicMock(
            backend="indy",
            created=True,
            name="Test Wallet",
            transaction=async_mock.CoroutineMock(return_value=self.session),
        )

        def _inject(cls, required=True):
            return self.injector.inject(cls, required=required)

        self.session.inject = _inject
        self.context = InjectionContext()
        self.context.injector.bind_instance(ProfileManager, MockManager(self.profile))

    async def test_wallet_config_existing_replace(self):
        self.context.update_settings(
            {
                "wallet.seed": "00000000000000000000000000000000",
                "wallet.replace_public_did": True,
                "debug.enabled": True,
            }
        )
        mock_wallet = async_mock.MagicMock(
            get_public_did=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(did=TEST_DID, verkey=TEST_VERKEY)
            ),
            set_public_did=async_mock.CoroutineMock(),
            create_local_did=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(did=TEST_DID, verkey=TEST_VERKEY)
            ),
        )
        self.injector.bind_instance(BaseWallet, mock_wallet)

        with async_mock.patch.object(
            test_module, "seed_to_did", async_mock.MagicMock()
        ) as mock_seed_to_did:
            mock_seed_to_did.return_value = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

            await test_module.wallet_config(self.context, provision=True)

    async def test_wallet_config_existing_open(self):
        self.profile = async_mock.MagicMock(
            backend="indy",
            created=False,
            name="Test Wallet",
            transaction=async_mock.CoroutineMock(return_value=self.session),
        )
        self.context.injector.clear_binding(ProfileManager)
        self.context.injector.bind_instance(ProfileManager, MockManager(self.profile))

        self.context.update_settings(
            {
                "wallet.seed": "00000000000000000000000000000000",
                "wallet.replace_public_did": True,
                "debug.enabled": True,
            }
        )
        mock_wallet = async_mock.MagicMock(
            get_public_did=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(did=TEST_DID, verkey=TEST_VERKEY)
            ),
            set_public_did=async_mock.CoroutineMock(),
            create_local_did=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(did=TEST_DID, verkey=TEST_VERKEY)
            ),
        )
        self.injector.bind_instance(BaseWallet, mock_wallet)

        self.context.injector.bind_instance(ProfileManager, MockManager(self.profile))

        with async_mock.patch.object(
            test_module, "seed_to_did", async_mock.MagicMock()
        ) as mock_seed_to_did:
            mock_seed_to_did.return_value = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

            await test_module.wallet_config(self.context, provision=True)

    async def test_wallet_config_auto_provision(self):
        self.context.update_settings(
            {
                "wallet.seed": "00000000000000000000000000000000",
                "wallet.replace_public_did": True,
                "debug.enabled": True,
                "auto_provision": False,
            }
        )
        mock_wallet = async_mock.MagicMock(
            get_public_did=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(did=TEST_DID, verkey=TEST_VERKEY)
            ),
            set_public_did=async_mock.CoroutineMock(),
            create_local_did=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(did=TEST_DID, verkey=TEST_VERKEY)
            ),
        )
        self.injector.bind_instance(BaseWallet, mock_wallet)

        with async_mock.patch.object(
            MockManager, "open", async_mock.CoroutineMock()
        ) as mock_mgr_open:
            mock_mgr_open.side_effect = test_module.ProfileNotFoundError()

            with self.assertRaises(test_module.ProfileNotFoundError):
                await test_module.wallet_config(self.context, provision=False)

            self.context.update_settings({"auto_provision": True})
            await test_module.wallet_config(self.context, provision=False)

    async def test_wallet_config_non_indy_x(self):
        self.context.update_settings(
            {
                "wallet.seed": "00000000000000000000000000000000",
            }
        )
        self.profile.backend = "not-indy"
        mock_wallet = async_mock.MagicMock(
            get_public_did=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(did=TEST_DID, verkey=TEST_VERKEY)
            ),
        )
        self.injector.bind_instance(BaseWallet, mock_wallet)

        with self.assertRaises(test_module.ConfigError):
            await test_module.wallet_config(self.context, provision=True)

    async def test_wallet_config_bad_seed_x(self):
        self.context.update_settings(
            {
                "wallet.seed": "00000000000000000000000000000000",
            }
        )
        mock_wallet = async_mock.MagicMock(
            get_public_did=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(did=TEST_DID, verkey=TEST_VERKEY)
            ),
        )
        self.injector.bind_instance(BaseWallet, mock_wallet)

        with async_mock.patch.object(
            test_module,
            "seed_to_did",
            async_mock.MagicMock(return_value="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"),
        ) as mock_seed_to_did:

            with self.assertRaises(test_module.ConfigError):
                await test_module.wallet_config(self.context, provision=True)

    async def test_wallet_config_seed_local(self):
        self.context.update_settings(
            {
                "wallet.seed": "00000000000000000000000000000000",
                "wallet.local_did": True,
            }
        )
        mock_wallet = async_mock.MagicMock(
            get_public_did=async_mock.CoroutineMock(return_value=None),
            set_public_did=async_mock.CoroutineMock(),
            create_local_did=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(did=TEST_DID, verkey=TEST_VERKEY)
            ),
        )
        self.injector.bind_instance(BaseWallet, mock_wallet)

        with async_mock.patch.object(
            test_module, "seed_to_did", async_mock.MagicMock()
        ) as mock_seed_to_did:
            mock_seed_to_did.return_value = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

            await test_module.wallet_config(self.context, provision=True)

    async def test_wallet_config_seed_public(self):
        self.context.update_settings(
            {
                "wallet.seed": "00000000000000000000000000000000",
            }
        )
        mock_wallet = async_mock.MagicMock(
            get_public_did=async_mock.CoroutineMock(return_value=None),
            set_public_did=async_mock.CoroutineMock(),
            create_public_did=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(did=TEST_DID, verkey=TEST_VERKEY)
            ),
        )
        self.injector.bind_instance(BaseWallet, mock_wallet)

        with async_mock.patch.object(
            test_module,
            "seed_to_did",
            async_mock.MagicMock(return_value="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"),
        ) as mock_seed_to_did:
            await test_module.wallet_config(self.context, provision=True)

    async def test_wallet_config_seed_no_public_did(self):
        mock_wallet = async_mock.MagicMock(
            get_public_did=async_mock.CoroutineMock(return_value=None),
            set_public_did=async_mock.CoroutineMock(),
            create_public_did=async_mock.CoroutineMock(
                return_value=async_mock.MagicMock(did=TEST_DID, verkey=TEST_VERKEY)
            ),
        )
        self.injector.bind_instance(BaseWallet, mock_wallet)

        with async_mock.patch.object(
            test_module, "seed_to_did", async_mock.MagicMock()
        ) as mock_seed_to_did:
            mock_seed_to_did.return_value = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

            await test_module.wallet_config(self.context, provision=True)
