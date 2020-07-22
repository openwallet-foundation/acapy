import pytest

from aries_cloudagent.wallet_handler.handler import WalletHandler
from aries_cloudagent.config.provider import DynamicProvider, StatsProvider
from aries_cloudagent.wallet.provider import WalletProvider
from aries_cloudagent.wallet.base import BaseWallet
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.storage.provider import StorageProvider

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

TEST_CONFIG = {}


@pytest.fixture()
async def wallet_handler():
    provider = DynamicProvider(
                WalletProvider(),
                "wallet.name"
            )
    wallet_handler = WalletHandler(provider, TEST_CONFIG)
    yield wallet_handler


class TestWalletHandler(AsyncTestCase):
    def setUp(self):
        self.context = InjectionContext(enforce_typing=False)
        self.context.injector.bind_provider(
            BaseWallet,
            DynamicProvider(
                StatsProvider(
                    WalletProvider(),
                    (
                        "sign_message",
                        "verify_message",
                        # "pack_message",
                        # "unpack_message",
                        "get_local_did",
                    ),
                ),
                'wallet.name'
            ),
        )
        self.context.injector.bind_provider(
            BaseStorage,
            #CachedProvider(
            StatsProvider(
                StorageProvider(), ("add_record", "get_record", "search_records")
            )
            #),
        )
        self.wallet = async_mock.create_autospec(BaseWallet)
        handeled_provider = self.context.injector._providers[BaseWallet]

        #self.context.injector.bind_instance(BaseWallet, self.wallet)
        self.wallet_handler = WalletHandler(handeled_provider, {})

        self.test_wallet_cfg = {
            "type": "indy",
            "key": "123456",
            "name": "Wallet1",
            "seed": "cccccccccccccccccccccccccccccccc"
        }
        self.test_wallet_cfg2 = {
            "type": "indy",
            "key": "123456",
            "name": "Wallet2",
            "seed": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        }

    def test_one(self):
        x = "this"
        assert "h" in x

    def test_properties(self):
        assert self.wallet_handler.WALLET_TYPE == 'indy'

    @pytest.mark.asyncio
    async def test_get_instances(self):
        instances = await self.wallet_handler.get_instances()

        assert instances == []

    @pytest.mark.asyncio
    async def test_handle_instances(self):
        """Test handling of wallets by wallet handler.

        Tests the following functionallities:
        - Adding multiple wallets to the handler.
        - Removing a wallet from the handler.

        """
        await self.wallet_handler.add_instance(self.test_wallet_cfg, self.context)
        await self.wallet_handler.add_instance(self.test_wallet_cfg2, self.context)
        wallets = await self.wallet_handler.get_instances()

        assert wallets == [
            self.test_wallet_cfg.get('name'),
            self.test_wallet_cfg2.get('name')
        ]

        await self.wallet_handler.delete_instance(self.test_wallet_cfg2.get('name'))
        wallets = await self.wallet_handler.get_instances()

        assert wallets == [
            self.test_wallet_cfg.get('name')
        ]

        await self.wallet_handler.delete_instance(self.test_wallet_cfg.get('name'))

    @pytest.mark.asyncio
    async def test_create_dids_for_wallets(self):
        await self.wallet_handler.add_instance(self.test_wallet_cfg, self.context)
        await self.wallet_handler.add_instance(self.test_wallet_cfg2, self.context)

        await self.wallet_handler.set_instance(self.test_wallet_cfg.get('name'))
        wallet1: BaseWallet = await self.context.inject(BaseWallet)
        assert wallet1.name == self.test_wallet_cfg.get('name')

        await self.wallet_handler.set_instance(self.test_wallet_cfg2.get('name'))
        wallet2: BaseWallet = await self.context.inject(BaseWallet)
        assert wallet2.name == self.test_wallet_cfg2.get('name')

        await self.wallet_handler.delete_instance(self.test_wallet_cfg.get('name'))
        await self.wallet_handler.delete_instance(self.test_wallet_cfg2.get('name'))
