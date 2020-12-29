from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

import jwt

from ...core.in_memory import InMemoryProfile
from ...config.base import InjectionError
from ...wallet.models.wallet_record import WalletRecord
from ...storage.error import StorageNotFoundError
from ...storage.in_memory import InMemoryStorage
from ...protocols.routing.v1_0.manager import RoutingManager
from ...protocols.routing.v1_0.models.route_record import RouteRecord
from ..manager import MultitenantManager, MultitenantManagerError
from ..error import WalletKeyMissingError


class TestMultitenantManager(AsyncTestCase):
    async def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.context = self.profile.context

        self.manager = MultitenantManager(self.profile)
        assert self.manager.profile

    async def test_init_throws_no_profile(self):
        with self.assertRaises(MultitenantManagerError):
            MultitenantManager(None)

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

    async def test_get_wallet_profile_not_in_cache(self):
        wallet_record = WalletRecord(wallet_id="test", settings={})
        self.manager._instances["test"] = InMemoryProfile.test_profile()

        with async_mock.patch(
            "aries_cloudagent.config.wallet.wallet_config"
        ) as wallet_config:
            profile = await self.manager.get_wallet_profile(
                self.profile.context, wallet_record
            )
            assert profile is self.manager._instances["test"]
            wallet_config.assert_not_called()

    async def test_get_wallet_profile_settings(self):
        extra_settings = {"extra_settings": "extra_settings"}
        wallet_record_settings = {"wallet_record_settings": "wallet_record_settings"}
        wallet_record = WalletRecord(
            wallet_id="test",
            settings=wallet_record_settings,
        )

        with async_mock.patch(
            "aries_cloudagent.multitenant.manager.wallet_config"
        ) as wallet_config:

            def side_effect(context, provision):
                return (InMemoryProfile(context=context), None)

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

        with async_mock.patch(
            "aries_cloudagent.multitenant.manager.wallet_config"
        ) as wallet_config:

            def side_effect(context, provision):
                return (InMemoryProfile(context=context), None)

            wallet_config.side_effect = side_effect

            profile = await self.manager.get_wallet_profile(
                self.profile.context, wallet_record
            )

            settings = profile.settings

            assert settings.get("wallet.recreate") == False
            assert settings.get("wallet.seed") == None
            assert settings.get("wallet.rekey") == None
            assert settings.get("wallet.name") == None
            assert settings.get("wallet.type") == None

    async def test_get_wallet_profile_settings_reset_overwrite(self):
        wallet_record = WalletRecord(
            wallet_id="test",
            settings={
                "wallet.recreate": True,
                "wallet.seed": "test_seed",
                "wallet.name": "test_name",
                "wallet.type": "test_type",
                "wallet.rekey": "test_rekey",
            },
        )

        with async_mock.patch(
            "aries_cloudagent.multitenant.manager.wallet_config"
        ) as wallet_config:

            def side_effect(context, provision):
                return (InMemoryProfile(context=context), None)

            wallet_config.side_effect = side_effect

            profile = await self.manager.get_wallet_profile(
                self.profile.context, wallet_record
            )

            settings = profile.settings

            assert settings.get("wallet.recreate") == True
            assert settings.get("wallet.seed") == "test_seed"
            assert settings.get("wallet.rekey") == "test_rekey"
            assert settings.get("wallet.name") == "test_name"
            assert settings.get("wallet.type") == "test_type"

    async def test_wallet_exists_name_is_root_profile_name(self):
        session = InMemoryProfile.test_session({"wallet.name": "test_wallet"})

        wallet_name_exists = await self.manager._wallet_name_exists(
            session, "test_wallet"
        )
        assert wallet_name_exists is True

    async def test_wallet_exists_in_wallet_record(self):
        session = InMemoryProfile.test_session({"wallet.name": "test_wallet"})

        # create wallet record with existing wallet_name
        wallet_record = WalletRecord(
            key_management_mode="managed",
            settings={"wallet.name": "another_test_wallet"},
        )
        await wallet_record.save(session)

        wallet_name_exists = await self.manager._wallet_name_exists(
            session, "another_test_wallet"
        )
        assert wallet_name_exists is True

    async def test_wallet_exists_false(self):
        session = InMemoryProfile.test_session({"wallet.name": "test_wallet"})

        wallet_name_exists = await self.manager._wallet_name_exists(
            session, "another_test_wallet"
        )
        assert wallet_name_exists is False

    async def test_get_wallet_by_key_routing_record_does_not_exist(self):
        session = InMemoryProfile.test_session()
        recipient_key = "test"

        with async_mock.patch.object(WalletRecord, "retrieve_by_id") as retrieve_by_id:
            wallet = await self.manager._get_wallet_by_key(session, recipient_key)

            assert wallet is None
            retrieve_by_id.assert_not_called()

        await self.manager._get_wallet_by_key(session, recipient_key)

    async def test_get_wallet_by_key_wallet_record_does_not_exist(self):
        session = InMemoryProfile.test_session()
        recipient_key = "test-recipient-key"
        wallet_id = "test-wallet-id"

        route_record = RouteRecord(wallet_id=wallet_id, recipient_key=recipient_key)
        await route_record.save(session)

        with self.assertRaises(StorageNotFoundError):
            await self.manager._get_wallet_by_key(session, recipient_key)

    async def test_get_wallet_by_key(self):
        session = InMemoryProfile.test_session()
        recipient_key = "test-recipient-key"

        wallet_record = WalletRecord(settings={})
        await wallet_record.save(session)

        route_record = RouteRecord(
            wallet_id=wallet_record.wallet_id, recipient_key=recipient_key
        )
        await route_record.save(session)

        wallet = await self.manager._get_wallet_by_key(session, recipient_key)

        assert isinstance(wallet, WalletRecord)

    async def test_create_wallet_removes_key_only_unmanaged_mode(self):
        with async_mock.patch.object(
            MultitenantManager, "get_wallet_profile"
        ) as get_wallet_profile:
            unmanaged_wallet_record = await self.manager.create_wallet(
                {"wallet.key": "test_key"}, WalletRecord.MODE_UNMANAGED
            )
            managed_wallet_record = await self.manager.create_wallet(
                {"wallet.key": "test_key"}, WalletRecord.MODE_MANAGED
            )

            assert unmanaged_wallet_record.settings.get("wallet.key") is None
            assert managed_wallet_record.settings.get("wallet.key") == "test_key"

    async def test_create_wallet_fails_if_wallet_name_exists(self):
        with async_mock.patch.object(
            MultitenantManager, "_wallet_name_exists"
        ) as _wallet_name_exists:
            _wallet_name_exists.return_value = True

            with self.assertRaises(
                MultitenantManagerError,
                msg="Wallet with name test_wallet already exists",
            ):
                await self.manager.create_wallet(
                    {"wallet.name": "test_wallet"}, WalletRecord.MODE_MANAGED
                )

    async def test_create_wallet_saves_wallet_record_creates_profile(self):
        with async_mock.patch.object(
            WalletRecord, "save"
        ) as wallet_record_save, async_mock.patch.object(
            MultitenantManager, "get_wallet_profile"
        ) as get_wallet_profile:
            wallet_record = await self.manager.create_wallet(
                {"wallet.name": "test_wallet", "wallet.key": "test_key"},
                WalletRecord.MODE_MANAGED,
            )

            wallet_record_save.assert_called_once()
            get_wallet_profile.assert_called_once_with(
                self.profile.context,
                wallet_record,
                {"wallet.key": "test_key"},
                provision=True,
            )
            assert isinstance(wallet_record, WalletRecord)
            assert wallet_record.wallet_name == "test_wallet"
            assert wallet_record.key_management_mode == WalletRecord.MODE_MANAGED
            assert wallet_record.wallet_key == "test_key"

    async def test_remove_wallet_fails_no_wallet_key_but_required(self):
        with async_mock.patch.object(WalletRecord, "retrieve_by_id") as retrieve_by_id:
            retrieve_by_id.return_value = WalletRecord(
                wallet_id="test",
                key_management_mode=WalletRecord.MODE_UNMANAGED,
                settings={"wallet.type": "indy"},
            )

            with self.assertRaises(WalletKeyMissingError):
                await self.manager.remove_wallet("test")

    async def test_remove_wallet_removes_profile_wallet_storage_records(self):
        with async_mock.patch.object(
            WalletRecord, "retrieve_by_id"
        ) as retrieve_by_id, async_mock.patch.object(
            MultitenantManager, "get_wallet_profile"
        ) as get_wallet_profile, async_mock.patch.object(
            InMemoryProfile, "remove"
        ) as remove_profile, async_mock.patch.object(
            WalletRecord, "delete_record"
        ) as wallet_delete_record, async_mock.patch.object(
            InMemoryStorage, "delete_all_records"
        ) as delete_all_records:
            wallet_record = WalletRecord(
                wallet_id="test",
                key_management_mode=WalletRecord.MODE_UNMANAGED,
                settings={"wallet.type": "indy", "wallet.key": "test_key"},
            )
            wallet_profile = InMemoryProfile.test_profile()

            self.manager._instances["test"] = wallet_profile
            retrieve_by_id.return_value = wallet_record
            get_wallet_profile.return_value = wallet_profile

            await self.manager.remove_wallet("test")

            assert "test" not in self.manager._instances
            get_wallet_profile.assert_called_once_with(
                self.profile.context, wallet_record, {"wallet.key": "test_key"}
            )
            remove_profile.assert_called_once_with()
            assert wallet_delete_record.call_count == 1
            delete_all_records.assert_called_once_with(
                RouteRecord.RECORD_TYPE, {"wallet_id": "test"}
            )

    async def test_add_wallet_route(self):
        with async_mock.patch.object(
            RoutingManager, "create_route_record"
        ) as create_route_record:
            await self.manager.add_wallet_route("wallet_id", "recipient_key")

            create_route_record.assert_called_once_with(
                recipient_key="recipient_key", internal_wallet_id="wallet_id"
            )

    async def test_create_auth_token_fails_no_wallet_key_but_required(self):
        self.profile.settings["multitenant.jwt_secret"] = "very_secret_jwt"
        wallet_record = WalletRecord(
            wallet_id="test_wallet",
            key_management_mode=WalletRecord.MODE_UNMANAGED,
            settings={"wallet.type": "indy"},
        )

        with self.assertRaises(WalletKeyMissingError):
            await self.manager.create_auth_token(wallet_record)

    async def test_create_auth_token_managed(self):
        self.profile.settings["multitenant.jwt_secret"] = "very_secret_jwt"
        wallet_record = WalletRecord(
            wallet_id="test_wallet",
            key_management_mode=WalletRecord.MODE_MANAGED,
            settings={},
        )

        expected_token = jwt.encode(
            {"wallet_id": wallet_record.wallet_id}, "very_secret_jwt"
        ).decode()

        token = self.manager.create_auth_token(wallet_record)

        assert expected_token == token

    async def test_create_auth_token_unmanaged(self):
        self.profile.settings["multitenant.jwt_secret"] = "very_secret_jwt"
        wallet_record = WalletRecord(
            wallet_id="test_wallet",
            key_management_mode=WalletRecord.MODE_UNMANAGED,
            settings={"wallet.type": "indy"},
        )

        expected_token = jwt.encode(
            {"wallet_id": wallet_record.wallet_id, "wallet_key": "test_key"},
            "very_secret_jwt",
        ).decode()

        token = self.manager.create_auth_token(wallet_record, "test_key")

        assert expected_token == token

    async def test_get_profile_for_token_invalid_token_raises(self):
        self.profile.settings["multitenant.jwt_secret"] = "very_secret_jwt"

        token = jwt.encode({"wallet_id": "test"}, "some_random_key").decode()

        with self.assertRaises(jwt.InvalidTokenError):
            await self.manager.get_profile_for_token(self.profile.context, token)

    async def test_get_profile_for_token_wallet_key_missing_raises(self):
        self.profile.settings["multitenant.jwt_secret"] = "very_secret_jwt"
        wallet_record = WalletRecord(
            key_management_mode=WalletRecord.MODE_UNMANAGED,
            settings={"wallet.type": "indy"},
        )
        session = await self.profile.session()
        await wallet_record.save(session)
        token = jwt.encode(
            {"wallet_id": wallet_record.wallet_id}, "very_secret_jwt", algorithm="HS256"
        ).decode()

        with self.assertRaises(WalletKeyMissingError):
            await self.manager.get_profile_for_token(self.profile.context, token)

    async def test_get_profile_for_token_managed_wallet(self):
        self.profile.settings["multitenant.jwt_secret"] = "very_secret_jwt"
        wallet_record = WalletRecord(
            key_management_mode=WalletRecord.MODE_MANAGED,
            settings={"wallet.type": "indy", "wallet.key": "wallet_key"},
        )

        session = await self.profile.session()
        await wallet_record.save(session)

        token = jwt.encode(
            {"wallet_id": wallet_record.wallet_id}, "very_secret_jwt", algorithm="HS256"
        ).decode()

        with async_mock.patch.object(
            MultitenantManager, "get_wallet_profile"
        ) as get_wallet_profile:
            mock_profile = InMemoryProfile.test_profile()
            get_wallet_profile.return_value = mock_profile

            profile = await self.manager.get_profile_for_token(
                self.profile.context, token
            )

            get_wallet_profile.assert_called_once_with(
                self.profile.context,
                wallet_record,
                {},
            )

            assert profile == mock_profile

    async def test_get_profile_for_token_unmanaged_wallet(self):
        self.profile.settings["multitenant.jwt_secret"] = "very_secret_jwt"
        wallet_record = WalletRecord(
            key_management_mode=WalletRecord.MODE_UNMANAGED,
            settings={"wallet.type": "indy"},
        )

        session = await self.profile.session()
        await wallet_record.save(session)

        token = jwt.encode(
            {"wallet_id": wallet_record.wallet_id, "wallet_key": "wallet_key"},
            "very_secret_jwt",
            algorithm="HS256",
        ).decode()

        with async_mock.patch.object(
            MultitenantManager, "get_wallet_profile"
        ) as get_wallet_profile:
            mock_profile = InMemoryProfile.test_profile()
            get_wallet_profile.return_value = mock_profile

            profile = await self.manager.get_profile_for_token(
                self.profile.context,
                token,
            )

            get_wallet_profile.assert_called_once_with(
                self.profile.context,
                wallet_record,
                {"wallet.key": "wallet_key"},
            )

            assert profile == mock_profile

    async def test_get_wallets_by_message_missing_wire_format_raises(self):
        with self.assertRaises(
            InjectionError,
        ):
            await self.manager.get_wallets_by_message({})

    async def test_get_wallets_by_message(self):
        message_body = async_mock.MagicMock()
        recipient_keys = ["1", "2", "3", "4"]

        mock_wire_format = async_mock.MagicMock(
            get_recipient_keys=lambda mesage_body: recipient_keys
        )

        return_wallets = [
            WalletRecord(settings={}),
            None,
            None,
            WalletRecord(settings={}),
        ]

        with async_mock.patch.object(
            MultitenantManager, "_get_wallet_by_key"
        ) as get_wallet_by_key:
            get_wallet_by_key.side_effect = return_wallets

            wallets = await self.manager.get_wallets_by_message(
                message_body, mock_wire_format
            )

            assert len(wallets) == 2
            assert wallets[0] == return_wallets[0]
            assert wallets[1] == return_wallets[3]
            assert get_wallet_by_key.call_count == 4