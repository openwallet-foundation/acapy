from typing import Any
from unittest import mock
from unittest.mock import MagicMock, Mock

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ...config.injection_context import InjectionContext
from ...core.in_memory import InMemoryProfile
from ...messaging.responder import BaseResponder
from ...wallet.models.wallet_record import WalletRecord
from ..askar_profile_manager import AskarProfileMultitenantManager

class TestAskarProfileMultitenantManager(AsyncTestCase):
    async def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.context = self.profile.context

        self.responder = async_mock.CoroutineMock(send=async_mock.CoroutineMock())
        self.context.injector.bind_instance(BaseResponder, self.responder)

        self.manager = AskarProfileMultitenantManager(self.profile)

    async def test_get_wallet_profile_should_open_store_and_return_profile_with_wallet_context(self):
        wallet_record = WalletRecord(
            wallet_id="test",
            settings={
                "wallet.recreate": True,
                "wallet.seed": "test_seed",
                "wallet.name": "test_name",
                "wallet.type": "test_type",
                "wallet.rekey": "test_rekey",
                "mediation.open": True,
                "mediation.invite": "http://invite.com",
                "mediation.default_id": "24a96ef5",
                "mediation.clear": True,
            },
        )

        with async_mock.patch(
            "aries_cloudagent.multitenant.askar_profile_manager.wallet_config"
        ) as wallet_config:
            with async_mock.patch(
                    "aries_cloudagent.multitenant.askar_profile_manager.AskarProfile"
            ) as AskarProfile:
                sub_wallet_profile_context = InjectionContext()
                sub_wallet_profile = AskarProfile(None, context=InjectionContext())
                sub_wallet_profile.context.copy.return_value = sub_wallet_profile_context

                def side_effect(context, provision):
                    return sub_wallet_profile, None

                wallet_config.side_effect = side_effect

                await self.manager.get_wallet_profile(self.profile.context, wallet_record)

                wallet_config.assert_called_once()
                assert wallet_config.call_args[0][0].settings.get("wallet.name") == "multitenant_sub_wallet"
                AskarProfile.assert_called_with(sub_wallet_profile.opened, sub_wallet_profile_context)
                assert sub_wallet_profile_context.settings.get("wallet.seed") == "test_seed"
                assert sub_wallet_profile_context.settings.get("wallet.rekey") == "test_rekey"
                assert sub_wallet_profile_context.settings.get("wallet.name") == "test_name"
                assert sub_wallet_profile_context.settings.get("wallet.type") == "test_type"
                assert sub_wallet_profile_context.settings.get("mediation.open") == True
                assert sub_wallet_profile_context.settings.get("mediation.invite") == "http://invite.com"
                assert sub_wallet_profile_context.settings.get("mediation.default_id") == "24a96ef5"
                assert sub_wallet_profile_context.settings.get("mediation.clear") == True
                assert sub_wallet_profile_context.settings.get("wallet.id") == "test"
                assert sub_wallet_profile_context.settings.get("wallet.name") == "test_name"

