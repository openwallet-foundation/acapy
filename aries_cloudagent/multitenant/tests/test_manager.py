from unittest import IsolatedAsyncioTestCase
from aries_cloudagent.tests import mock

from ...core.in_memory import InMemoryProfile
from ...messaging.responder import BaseResponder
from ...wallet.models.wallet_record import WalletRecord
from ..manager import MultitenantManager


class TestMultitenantManager(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.context = self.profile.context

        self.responder = mock.CoroutineMock(send=mock.CoroutineMock())
        self.context.injector.bind_instance(BaseResponder, self.responder)

        self.manager = MultitenantManager(self.profile)

    async def test_get_wallet_profile_returns_from_cache(self):
        wallet_record = WalletRecord(wallet_id="test")
        self.manager._profiles.put("test", InMemoryProfile.test_profile())

        with mock.patch(
            "aries_cloudagent.config.wallet.wallet_config"
        ) as wallet_config:
            profile = await self.manager.get_wallet_profile(
                self.profile.context, wallet_record
            )
            assert profile is self.manager._profiles.get("test")
            wallet_config.assert_not_called()

    async def test_get_wallet_profile_not_in_cache(self):
        wallet_record = WalletRecord(wallet_id="test", settings={})
        self.manager._profiles.put("test", InMemoryProfile.test_profile())
        self.profile.context.update_settings(
            {"admin.webhook_urls": ["http://localhost:8020"]}
        )

        with mock.patch(
            "aries_cloudagent.config.wallet.wallet_config"
        ) as wallet_config:
            profile = await self.manager.get_wallet_profile(
                self.profile.context, wallet_record
            )
            assert profile is self.manager._profiles.get("test")
            wallet_config.assert_not_called()

    async def test_get_wallet_profile_settings(self):
        extra_settings = {"extra_settings": "extra_settings"}
        all_wallet_record_settings = [
            {
                "wallet_record_settings": "wallet_record_settings",
                "wallet.dispatch_type": "default",
            },
            {
                "wallet_record_settings": "wallet_record_settings",
                "wallet.dispatch_type": "default",
                "wallet.webhook_urls": ["https://localhost:8090"],
            },
            {
                "wallet_record_settings": "wallet_record_settings",
                "wallet.dispatch_type": "both",
            },
            {
                "wallet_record_settings": "wallet_record_settings",
                "wallet.dispatch_type": "both",
                "wallet.webhook_urls": ["https://localhost:8090"],
            },
        ]

        def side_effect(context, provision):
            return (InMemoryProfile(context=context), None)

        for idx, wallet_record_settings in enumerate(all_wallet_record_settings):
            wallet_record = WalletRecord(
                wallet_id=f"test.{idx}",
                settings=wallet_record_settings,
            )

            with mock.patch(
                "aries_cloudagent.multitenant.manager.wallet_config"
            ) as wallet_config:
                wallet_config.side_effect = side_effect
                profile = await self.manager.get_wallet_profile(
                    self.profile.context, wallet_record, extra_settings
                )

                assert (
                    profile.settings.get("wallet_record_settings")
                    == "wallet_record_settings"
                )
                assert profile.settings.get("extra_settings") == "extra_settings"

    async def test_get_wallet_profile_settings_reset(self):
        wallet_record = WalletRecord(
            wallet_id="test",
            settings={},
        )

        with mock.patch(
            "aries_cloudagent.multitenant.manager.wallet_config"
        ) as wallet_config:

            def side_effect(context, provision):
                return (InMemoryProfile(context=context), None)

            wallet_config.side_effect = side_effect

            self.profile.context.update_settings(
                {
                    "wallet.recreate": True,
                    "wallet.seed": "test_seed",
                    "wallet.name": "test_name",
                    "wallet.type": "test_type",
                    "wallet.rekey": "test_rekey",
                    "mediation.open": True,
                    "mediation.invite": "http://invite.com",
                    "mediation.default_id": "24a96ef5",
                    "mediation.clear": True,
                }
            )

            profile = await self.manager.get_wallet_profile(
                self.profile.context, wallet_record
            )

            assert profile.settings.get("wallet.recreate") is False
            assert profile.settings.get("wallet.seed") is None
            assert profile.settings.get("wallet.rekey") is None
            assert profile.settings.get("wallet.name") is None
            assert profile.settings.get("wallet.type") is None
            assert profile.settings.get("mediation.open") is None
            assert profile.settings.get("mediation.invite") is None
            assert profile.settings.get("mediation.default_id") is None
            assert profile.settings.get("mediation.clear") is None

    async def test_get_wallet_profile_settings_reset_overwrite(self):
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

        with mock.patch(
            "aries_cloudagent.multitenant.manager.wallet_config"
        ) as wallet_config:

            def side_effect(context, provision):
                return (InMemoryProfile(context=context), None)

            wallet_config.side_effect = side_effect

            profile = await self.manager.get_wallet_profile(
                self.profile.context, wallet_record
            )

            assert profile.settings.get("wallet.recreate") is True
            assert profile.settings.get("wallet.seed") == "test_seed"
            assert profile.settings.get("wallet.rekey") == "test_rekey"
            assert profile.settings.get("wallet.name") == "test_name"
            assert profile.settings.get("wallet.type") == "test_type"
            assert profile.settings.get("mediation.open") is True
            assert profile.settings.get("mediation.invite") == "http://invite.com"
            assert profile.settings.get("mediation.default_id") == "24a96ef5"
            assert profile.settings.get("mediation.clear") is True

    async def test_update_wallet_update_wallet_profile(self):
        with mock.patch.object(
            WalletRecord, "retrieve_by_id"
        ) as retrieve_by_id, mock.patch.object(
            WalletRecord, "save"
        ) as wallet_record_save:
            wallet_id = "test-wallet-id"
            wallet_profile = InMemoryProfile.test_profile()
            self.manager._profiles.put("test-wallet-id", wallet_profile)
            retrieve_by_id.return_value = WalletRecord(
                wallet_id=wallet_id,
                settings={
                    "wallet.webhook_urls": ["test-webhook-url"],
                    "wallet.dispatch_type": "both",
                },
            )

            new_settings = {
                "wallet.webhook_urls": ["new-webhook-url"],
                "wallet.dispatch_type": "default",
            }
            wallet_record = await self.manager.update_wallet(wallet_id, new_settings)

            wallet_record_save.assert_called_once()

            assert isinstance(wallet_record, WalletRecord)
            assert wallet_record.wallet_webhook_urls == ["new-webhook-url"]
            assert wallet_record.wallet_dispatch_type == "default"
            assert wallet_profile.settings.get("wallet.webhook_urls") == [
                "new-webhook-url"
            ]
            assert wallet_profile.settings.get("wallet.dispatch_type") == "default"

    async def test_remove_wallet_profile(self):
        test_profile = InMemoryProfile.test_profile(
            settings={"wallet.id": "test"},
        )
        self.manager._profiles.put("test", test_profile)

        with mock.patch.object(InMemoryProfile, "remove") as profile_remove:
            await self.manager.remove_wallet_profile(test_profile)
            assert not self.manager._profiles.has("test")
            profile_remove.assert_called_once_with()
