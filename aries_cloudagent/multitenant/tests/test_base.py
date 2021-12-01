from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

import jwt

from ...core.in_memory import InMemoryProfile
from ...config.base import InjectionError
from ...messaging.responder import BaseResponder
from ...wallet.models.wallet_record import WalletRecord
from ...wallet.in_memory import InMemoryWallet
from ...wallet.did_info import DIDInfo
from ...storage.error import StorageNotFoundError
from ...storage.in_memory import InMemoryStorage
from ...protocols.routing.v1_0.manager import RoutingManager
from ...protocols.routing.v1_0.models.route_record import RouteRecord
from ...protocols.coordinate_mediation.v1_0.manager import (
    MediationRecord,
    MediationManager,
)
from ...wallet.key_type import KeyType
from ...wallet.did_method import DIDMethod
from ..base import BaseMultitenantManager, MultitenantManagerError
from ..error import WalletKeyMissingError


class TestBaseMultitenantManager(AsyncTestCase):
    async def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.context = self.profile.context

        self.responder = async_mock.CoroutineMock(send=async_mock.CoroutineMock())
        self.context.injector.bind_instance(BaseResponder, self.responder)

        self.manager = BaseMultitenantManager(self.profile)

    async def test_init_throws_no_profile(self):
        with self.assertRaises(MultitenantManagerError):
            BaseMultitenantManager(None)

    async def test_get_default_mediator(self):
        with async_mock.patch.object(
            MediationManager, "get_default_mediator"
        ) as get_default_mediator:
            mediaton_record = MediationRecord()

            # has default mediator
            get_default_mediator.return_value = mediaton_record
            default_mediator = await self.manager.get_default_mediator()
            assert default_mediator is mediaton_record

            # Doesn't have default mediator
            get_default_mediator.return_value = None
            default_mediator = await self.manager.get_default_mediator()
            assert default_mediator is None

    async def test_get_webhook_urls_dispatch_type_base(self):
        wallet_record = WalletRecord(
            settings={
                "wallet.dispatch_type": "base",
                "wallet.webhook_urls": ["subwallet-webhook-url"],
            },
        )
        self.context.update_settings({"admin.webhook_urls": ["base-webhook-url"]})
        webhook_urls = self.manager.get_webhook_urls(self.context, wallet_record)
        assert webhook_urls == ["base-webhook-url"]

    async def test_get_webhook_urls_dispatch_type_default(self):
        wallet_record = WalletRecord(
            settings={
                "wallet.dispatch_type": "default",
                "wallet.webhook_urls": ["subwallet-webhook-url"],
            },
        )
        self.context.update_settings({"admin.webhook_urls": ["base-webhook-url"]})
        webhook_urls = self.manager.get_webhook_urls(self.context, wallet_record)
        assert webhook_urls == ["subwallet-webhook-url"]

    async def test_get_webhook_urls_dispatch_type_both(self):
        wallet_record = WalletRecord(
            settings={
                "wallet.dispatch_type": "both",
                "wallet.webhook_urls": ["subwallet-webhook-url"],
            },
        )
        self.context.update_settings({"admin.webhook_urls": ["base-webhook-url"]})
        webhook_urls = self.manager.get_webhook_urls(self.context, wallet_record)
        assert "base-webhook-url" in webhook_urls
        assert "subwallet-webhook-url" in webhook_urls

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
        recipient_key = "test"

        with async_mock.patch.object(WalletRecord, "retrieve_by_id") as retrieve_by_id:
            wallet = await self.manager._get_wallet_by_key(recipient_key)

            assert wallet is None
            retrieve_by_id.assert_not_called()

        await self.manager._get_wallet_by_key(recipient_key)

    async def test_get_wallet_by_key_wallet_record_does_not_exist(self):
        recipient_key = "test-recipient-key"
        wallet_id = "test-wallet-id"

        route_record = RouteRecord(wallet_id=wallet_id, recipient_key=recipient_key)
        async with self.profile.session() as session:
            await route_record.save(session)

        with self.assertRaises(StorageNotFoundError):
            await self.manager._get_wallet_by_key(recipient_key)

    async def test_get_wallet_by_key(self):
        recipient_key = "test-recipient-key"

        wallet_record = WalletRecord(settings={})
        async with self.profile.session() as session:
            await wallet_record.save(session)

            route_record = RouteRecord(
                wallet_id=wallet_record.wallet_id, recipient_key=recipient_key
            )
            await route_record.save(session)

        wallet = await self.manager._get_wallet_by_key(recipient_key)

        assert isinstance(wallet, WalletRecord)

    async def test_create_wallet_removes_key_only_unmanaged_mode(self):
        with async_mock.patch.object(
            BaseMultitenantManager, "get_wallet_profile"
        ) as get_wallet_profile:
            get_wallet_profile.return_value = InMemoryProfile.test_profile()

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
            BaseMultitenantManager, "_wallet_name_exists"
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
            BaseMultitenantManager, "get_wallet_profile"
        ) as get_wallet_profile, async_mock.patch.object(
            BaseMultitenantManager, "add_key"
        ) as add_key:
            get_wallet_profile.return_value = InMemoryProfile.test_profile()

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
            add_key.assert_not_called()
            assert isinstance(wallet_record, WalletRecord)
            assert wallet_record.wallet_name == "test_wallet"
            assert wallet_record.key_management_mode == WalletRecord.MODE_MANAGED
            assert wallet_record.wallet_key == "test_key"

    async def test_create_wallet_adds_wallet_route(self):
        did_info = DIDInfo(
            did="public-did",
            verkey="test_verkey",
            metadata={"meta": "data"},
            method=DIDMethod.SOV,
            key_type=KeyType.ED25519,
        )

        with async_mock.patch.object(
            WalletRecord, "save"
        ) as wallet_record_save, async_mock.patch.object(
            BaseMultitenantManager, "get_wallet_profile"
        ) as get_wallet_profile, async_mock.patch.object(
            BaseMultitenantManager, "add_key"
        ) as add_key, async_mock.patch.object(
            InMemoryWallet, "get_public_did"
        ) as get_public_did:
            get_wallet_profile.return_value = InMemoryProfile.test_profile()
            get_public_did.return_value = did_info

            wallet_record = await self.manager.create_wallet(
                {"wallet.name": "test_wallet", "wallet.key": "test_key"},
                WalletRecord.MODE_MANAGED,
            )

            add_key.assert_called_once_with(
                wallet_record.wallet_id, did_info.verkey, skip_if_exists=True
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

    async def test_update_wallet_update_wallet_profile(self):
        with async_mock.patch.object(
            WalletRecord, "retrieve_by_id"
        ) as retrieve_by_id, async_mock.patch.object(
            WalletRecord, "save"
        ) as wallet_record_save:
            wallet_id = "test-wallet-id"
            wallet_profile = InMemoryProfile.test_profile()
            self.manager._instances["test-wallet-id"] = wallet_profile
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
            BaseMultitenantManager, "get_wallet_profile"
        ) as get_wallet_profile, async_mock.patch.object(
            BaseMultitenantManager, "remove_wallet_profile"
        ) as remove_wallet_profile, async_mock.patch.object(
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

            retrieve_by_id.return_value = wallet_record
            get_wallet_profile.return_value = wallet_profile

            await self.manager.remove_wallet("test")

            get_wallet_profile.assert_called_once_with(
                self.profile.context, wallet_record, {"wallet.key": "test_key"}
            )
            remove_wallet_profile.assert_called_once_with(wallet_profile)
            assert wallet_delete_record.call_count == 1
            delete_all_records.assert_called_once_with(
                RouteRecord.RECORD_TYPE, {"wallet_id": "test"}
            )

    async def test_add_key_no_mediation(self):
        with async_mock.patch.object(
            RoutingManager, "create_route_record"
        ) as create_route_record, async_mock.patch.object(
            MediationManager, "add_key"
        ) as mediation_add_key:
            await self.manager.add_key("wallet_id", "recipient_key")

            create_route_record.assert_called_once_with(
                recipient_key="recipient_key", internal_wallet_id="wallet_id"
            )
            mediation_add_key.assert_not_called()

    async def test_add_key_skip_if_exists_does_not_exist(self):
        with async_mock.patch.object(
            RoutingManager, "create_route_record"
        ) as create_route_record, async_mock.patch.object(
            RouteRecord, "retrieve_by_recipient_key"
        ) as retrieve_by_recipient_key:
            retrieve_by_recipient_key.side_effect = StorageNotFoundError()

            await self.manager.add_key(
                "wallet_id", "recipient_key", skip_if_exists=True
            )

            create_route_record.assert_called_once_with(
                recipient_key="recipient_key", internal_wallet_id="wallet_id"
            )

    async def test_add_key_skip_if_exists_does_exist(self):
        with async_mock.patch.object(
            RoutingManager, "create_route_record"
        ) as create_route_record, async_mock.patch.object(
            RouteRecord, "retrieve_by_recipient_key"
        ) as retrieve_by_recipient_key:
            await self.manager.add_key(
                "wallet_id", "recipient_key", skip_if_exists=True
            )

            create_route_record.assert_not_called()

    async def test_add_key_mediation(self):
        with async_mock.patch.object(
            RoutingManager, "create_route_record"
        ) as create_route_record, async_mock.patch.object(
            MediationManager, "get_default_mediator"
        ) as get_default_mediator, async_mock.patch.object(
            MediationManager, "add_key"
        ) as mediation_add_key:
            default_mediator = async_mock.CoroutineMock()
            keylist_updates = async_mock.CoroutineMock()

            get_default_mediator.return_value = default_mediator
            mediation_add_key.return_value = keylist_updates

            await self.manager.add_key("wallet_id", "recipient_key")

            create_route_record.assert_called_once_with(
                recipient_key="recipient_key", internal_wallet_id="wallet_id"
            )

            get_default_mediator.assert_called_once()
            mediation_add_key.assert_called_once_with("recipient_key")
            self.responder.send.assert_called_once_with(
                keylist_updates, connection_id=default_mediator.connection_id
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
            BaseMultitenantManager, "get_wallet_profile"
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
            BaseMultitenantManager, "get_wallet_profile"
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
            BaseMultitenantManager, "_get_wallet_by_key"
        ) as get_wallet_by_key:
            get_wallet_by_key.side_effect = return_wallets

            wallets = await self.manager.get_wallets_by_message(
                message_body, mock_wire_format
            )

            assert len(wallets) == 2
            assert wallets[0] == return_wallets[0]
            assert wallets[1] == return_wallets[3]
            assert get_wallet_by_key.call_count == 4
