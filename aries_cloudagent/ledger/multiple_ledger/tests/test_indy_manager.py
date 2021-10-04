from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from collections import OrderedDict

from ....core.in_memory import InMemoryProfile
from ....messaging.responder import BaseResponder
from ..manager import MultiIndyLedgerManager


class TestMultiIndyLedgerManager(AsyncTestCase):
    async def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.context = self.profile.context

        self.responder = async_mock.CoroutineMock(send=async_mock.CoroutineMock())
        self.context.injector.bind_instance(BaseResponder, self.responder)
        self.production_ledger = OrderedDict()
        self.non_production_ledger =  OrderedDict()
        self.manager = MultiIndyLedgerManager(self.profile)

    async def test_get_wallet_profile_returns_from_cache(self):
        wallet_record = WalletRecord(wallet_id="test")
        self.manager._instances["test"] = InMemoryProfile.test_profile()

        with async_mock.patch(
            "aries_cloudagent.config.wallet.wallet_config"
        ) as wallet_config:
            profile = await self.manager.get_wallet_profile(
                self.profile.context, wallet_record
            )
            assert profile is self.manager._instances["test"]
            wallet_config.assert_not_called()