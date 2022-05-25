from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
from marshmallow.exceptions import ValidationError

from ...base import BaseMultitenantManager, MultitenantManagerError
from ....admin.request_context import AdminRequestContext
from ....wallet.models.wallet_record import WalletRecord
from ....messaging.models.base import BaseModelError
from ....storage.error import StorageError, StorageNotFoundError

from .. import routes as test_module


class TestMultitenantRoutes(AsyncTestCase):
    async def setUp(self):
        self.mock_multitenant_mgr = async_mock.MagicMock(
            __aexit__=async_mock.CoroutineMock(), autospec=True
        )
        self.mock_multitenant_mgr.__aenter__ = async_mock.CoroutineMock(
            return_value=self.mock_multitenant_mgr
        )

        self.context = AdminRequestContext.test_context()
        self.context.profile.context.injector.bind_instance(
            BaseMultitenantManager, self.mock_multitenant_mgr
        )

        self.request_dict = {
            "context": self.context,
            "outbound_message_router": async_mock.CoroutineMock(),
        }
        self.request = async_mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
        )

    async def test_format_wallet_record_removes_wallet_key(self):
        wallet_record = WalletRecord(
            wallet_id="test",
            key_management_mode=WalletRecord.MODE_MANAGED,
            settings={"wallet.name": "wallet_name", "wallet.key": "wallet_key"},
        )

        formatted = test_module.format_wallet_record(wallet_record)

        assert "wallet.key" not in formatted["settings"]

    async def test_wallets_list(self):
        with async_mock.patch.object(
            test_module, "WalletRecord", autospec=True
        ) as mock_wallet_record, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            wallets = [
                async_mock.MagicMock(
                    serialize=async_mock.MagicMock(
                        return_value={
                            "wallet_id": "wallet_id",
                            "created_at": "1234567890",
                            "settings": {"wallet.name": "test"},
                        }
                    )
                ),
                async_mock.MagicMock(
                    serialize=async_mock.MagicMock(
                        return_value={
                            "wallet_id": "wallet_id",
                            "created_at": "1234567891",
                            "settings": {"wallet.name": "test"},
                        }
                    )
                ),
                async_mock.MagicMock(
                    serialize=async_mock.MagicMock(
                        return_value={
                            "wallet_id": "wallet_id",
                            "created_at": "1234567892",
                            "settings": {"wallet.name": "test"},
                        }
                    )
                ),
            ]
            mock_wallet_record.query = async_mock.CoroutineMock()
            mock_wallet_record.query.return_value = [wallets[2], wallets[0], wallets[1]]

            await test_module.wallets_list(self.request)
            mock_response.assert_called_once_with(
                {"results": [test_module.format_wallet_record(w) for w in wallets]}
            )

    async def test_wallets_list_x(self):
        with async_mock.patch.object(
            test_module, "WalletRecord", autospec=True
        ) as mock_wallet_record:
            mock_wallet_record.query = async_mock.CoroutineMock()

            mock_wallet_record.query.side_effect = StorageError()
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.wallets_list(self.request)

            mock_wallet_record.query.side_effect = BaseModelError()
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.wallets_list(self.request)

    async def test_wallets_list_query(self):
        self.request.query = {"wallet_name": "test"}

        with async_mock.patch.object(
            test_module, "WalletRecord", autospec=True
        ) as mock_wallet_record, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            wallets = [
                async_mock.MagicMock(
                    serialize=async_mock.MagicMock(
                        return_value={
                            "wallet_id": "wallet_id",
                            "created_at": "1234567890",
                            "settings": {"wallet.name": "test"},
                        }
                    )
                ),
            ]
            mock_wallet_record.query = async_mock.CoroutineMock()
            mock_wallet_record.query.return_value = wallets

            await test_module.wallets_list(self.request)
            mock_response.assert_called_once_with(
                {
                    "results": [
                        {
                            "wallet_id": "wallet_id",
                            "created_at": "1234567890",
                            "settings": {"wallet.name": "test"},
                        }
                    ]
                }
            )

    async def test_wallet_create(self):
        body = {
            "wallet_name": "test",
            "default_label": "test_label",
            "wallet_type": "indy",
            "wallet_key": "test",
            "key_management_mode": "managed",
            "wallet_webhook_urls": [],
            "wallet_dispatch_type": "base",
        }
        self.request.json = async_mock.CoroutineMock(return_value=body)

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            wallet_mock = async_mock.MagicMock(
                serialize=async_mock.MagicMock(
                    return_value={
                        "wallet_id": "test",
                        "settings": {},
                        "key_management_mode": body["key_management_mode"],
                    }
                )
            )  # wallet_record
            self.mock_multitenant_mgr.create_wallet = async_mock.CoroutineMock(
                return_value=wallet_mock
            )

            self.mock_multitenant_mgr.create_auth_token = async_mock.CoroutineMock(
                return_value="test_token"
            )
            print(self.request["context"])
            await test_module.wallet_create(self.request)

            self.mock_multitenant_mgr.create_wallet.assert_called_once_with(
                {
                    "wallet.name": body["wallet_name"],
                    "wallet.type": body["wallet_type"],
                    "wallet.key": body["wallet_key"],
                    "wallet.webhook_urls": body["wallet_webhook_urls"],
                    "wallet.dispatch_type": body["wallet_dispatch_type"],
                },
                body["key_management_mode"],
            )
            self.mock_multitenant_mgr.create_auth_token.assert_called_once_with(
                wallet_mock, body["wallet_key"]
            )
            mock_response.assert_called_once_with(
                {**test_module.format_wallet_record(wallet_mock), "token": "test_token"}
            )

    async def test_wallet_create_x(self):
        body = {}
        self.request.json = async_mock.CoroutineMock(return_value=body)

        self.mock_multitenant_mgr.create_wallet.side_effect = MultitenantManagerError()
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_create(self.request)

    async def test_wallet_create_schema_validation_fails_indy_no_name_key(self):
        incorrect_body = {"wallet_type": "indy"}

        with self.assertRaises(ValidationError):
            schema = test_module.CreateWalletRequestSchema()
            schema.validate_fields(incorrect_body)

    async def test_wallet_create_optional_default_fields(self):
        body = {
            "wallet_name": "test",
            "wallet_key": "test",
            "wallet_key_derivation": "ARGON2I_MOD",
            "wallet_webhook_urls": [],
            "wallet_dispatch_type": "base",
            "label": "my_test_label",
            "image_url": "https://image.com",
        }
        self.request.json = async_mock.CoroutineMock(return_value=body)

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            self.mock_multitenant_mgr.create_wallet = async_mock.CoroutineMock()
            self.mock_multitenant_mgr.create_auth_token = async_mock.CoroutineMock()

            await test_module.wallet_create(self.request)
            self.mock_multitenant_mgr.create_wallet.assert_called_once_with(
                {
                    "wallet.name": body["wallet_name"],
                    "wallet.type": "in_memory",
                    "wallet.key": body["wallet_key"],
                    "default_label": body["label"],
                    "image_url": body["image_url"],
                    "wallet.webhook_urls": body["wallet_webhook_urls"],
                    "wallet.dispatch_type": body["wallet_dispatch_type"],
                    "wallet.key_derivation_method": body["wallet_key_derivation"],
                },
                WalletRecord.MODE_MANAGED,
            )

    async def test_wallet_create_raw_key_derivation(self):
        body = {
            "wallet_name": "test",
            "wallet_key": "test",
            "wallet_key_derivation": "RAW",
        }
        self.request.json = async_mock.CoroutineMock(return_value=body)

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            self.mock_multitenant_mgr.create_wallet = async_mock.CoroutineMock()
            self.mock_multitenant_mgr.create_auth_token = async_mock.CoroutineMock()

            await test_module.wallet_create(self.request)
            self.mock_multitenant_mgr.create_wallet.assert_called_once_with(
                {
                    "wallet.type": "in_memory",
                    "wallet.name": body["wallet_name"],
                    "wallet.key": body["wallet_key"],
                    "wallet.key_derivation_method": body["wallet_key_derivation"],
                    "wallet.webhook_urls": [],
                    "wallet.dispatch_type": "base",
                },
                WalletRecord.MODE_MANAGED,
            )

    async def test_wallet_update(self):
        self.request.match_info = {"wallet_id": "test-wallet-id"}
        body = {
            "wallet_webhook_urls": ["test-webhook-url"],
            "wallet_dispatch_type": "default",
            "label": "test-label",
            "image_url": "test-image-url",
        }
        self.request.json = async_mock.CoroutineMock(return_value=body)

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            settings = {
                "wallet.webhook_urls": body["wallet_webhook_urls"],
                "wallet.dispatch_type": body["wallet_dispatch_type"],
                "default_label": body["label"],
                "image_url": body["image_url"],
            }
            wallet_mock = async_mock.MagicMock(
                serialize=async_mock.MagicMock(
                    return_value={
                        "wallet_id": "test-wallet-id",
                        "settings": settings,
                    }
                )
            )
            self.mock_multitenant_mgr.update_wallet = async_mock.CoroutineMock(
                return_value=wallet_mock
            )

            await test_module.wallet_update(self.request)

            self.mock_multitenant_mgr.update_wallet.assert_called_once_with(
                "test-wallet-id",
                settings,
            )
            mock_response.assert_called_once_with(
                {"wallet_id": "test-wallet-id", "settings": settings}
            )

    async def test_wallet_update_no_wallet_webhook_urls(self):
        self.request.match_info = {"wallet_id": "test-wallet-id"}
        body = {
            "label": "test-label",
            "image_url": "test-image-url",
        }
        self.request.json = async_mock.CoroutineMock(return_value=body)

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            settings = {
                "default_label": body["label"],
                "image_url": body["image_url"],
            }
            wallet_mock = async_mock.MagicMock(
                serialize=async_mock.MagicMock(
                    return_value={
                        "wallet_id": "test-wallet-id",
                        "settings": settings,
                    }
                )
            )
            self.mock_multitenant_mgr.update_wallet = async_mock.CoroutineMock(
                return_value=wallet_mock
            )

            await test_module.wallet_update(self.request)

            self.mock_multitenant_mgr.update_wallet.assert_called_once_with(
                "test-wallet-id",
                settings,
            )
            mock_response.assert_called_once_with(
                {"wallet_id": "test-wallet-id", "settings": settings}
            )

    async def test_wallet_update_empty_wallet_webhook_urls(self):
        self.request.match_info = {"wallet_id": "test-wallet-id"}
        body = {
            "wallet_webhook_urls": [],
            "label": "test-label",
            "image_url": "test-image-url",
        }
        self.request.json = async_mock.CoroutineMock(return_value=body)

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            settings = {
                "wallet.webhook_urls": [],
                "wallet.dispatch_type": "base",
                "default_label": body["label"],
                "image_url": body["image_url"],
            }
            wallet_mock = async_mock.MagicMock(
                serialize=async_mock.MagicMock(
                    return_value={
                        "wallet_id": "test-wallet-id",
                        "settings": settings,
                    }
                )
            )
            self.mock_multitenant_mgr.update_wallet = async_mock.CoroutineMock(
                return_value=wallet_mock
            )

            await test_module.wallet_update(self.request)

            self.mock_multitenant_mgr.update_wallet.assert_called_once_with(
                "test-wallet-id",
                settings,
            )
            mock_response.assert_called_once_with(
                {"wallet_id": "test-wallet-id", "settings": settings}
            )

    async def test_wallet_update_wallet_settings_x(self):
        self.request.match_info = {"wallet_id": "test-wallet-id"}
        body = {
            "wallet_webhook_urls": ["test-webhook-url"],
            "label": "test-label",
            "image_url": "test-image-url",
        }
        self.request.json = async_mock.CoroutineMock(return_value=body)

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            self.mock_multitenant_mgr.update_wallet = async_mock.CoroutineMock(
                side_effect=test_module.WalletSettingsError("bad settings")
            )

            with self.assertRaises(test_module.web.HTTPBadRequest) as context:
                await test_module.wallet_update(self.request)
            assert "bad settings" in str(context.exception)

    async def test_wallet_update_no_params(self):
        self.request.match_info = {"wallet_id": "test-wallet-id"}
        body = {}
        self.request.json = async_mock.CoroutineMock(return_value=body)

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_update(self.request)

    async def test_wallet_update_not_found(self):
        self.request.match_info = {"wallet_id": "test-wallet-id"}
        body = {"label": "test-label"}
        self.request.json = async_mock.CoroutineMock(return_value=body)
        self.mock_multitenant_mgr.update_wallet = async_mock.CoroutineMock(
            side_effect=StorageNotFoundError()
        )

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.wallet_update(self.request)

    async def test_wallet_get(self):
        self.request.match_info = {"wallet_id": "dummy"}
        mock_wallet_record = async_mock.MagicMock()
        mock_wallet_record.serialize = async_mock.MagicMock(
            return_value={"settings": {}, "wallet_id": "dummy"}
        )

        with async_mock.patch.object(
            test_module.WalletRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_wallet_record_retrieve_by_id, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_wallet_record_retrieve_by_id.return_value = mock_wallet_record

            await test_module.wallet_get(self.request)
            mock_response.assert_called_once_with(
                {"settings": {}, "wallet_id": "dummy"}
            )

    async def test_wallet_get_not_found(self):
        self.request.match_info = {"wallet_id": "dummy"}

        with async_mock.patch.object(
            test_module.WalletRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_wallet_record_retrieve_by_id:
            mock_wallet_record_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.wallet_get(self.request)

    async def test_wallet_get_x(self):
        self.request.match_info = {"wallet_id": "dummy"}
        mock_wallet_record = async_mock.MagicMock()
        mock_wallet_record.serialize = async_mock.MagicMock(
            side_effect=test_module.BaseModelError()
        )

        with async_mock.patch.object(
            test_module.WalletRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_wallet_record_retrieve_by_id:
            mock_wallet_record_retrieve_by_id.return_value = mock_wallet_record

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.wallet_get(self.request)

    async def test_wallet_create_token_managed(self):
        self.request.has_body = False
        self.request.match_info = {"wallet_id": "dummy"}
        mock_wallet_record = async_mock.MagicMock()
        mock_wallet_record.serialize = async_mock.MagicMock(
            return_value={"settings": {}, "wallet_id": "dummy"}
        )

        with async_mock.patch.object(
            test_module.WalletRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_wallet_record_retrieve_by_id, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_wallet_record_retrieve_by_id.return_value = mock_wallet_record

            self.mock_multitenant_mgr.create_auth_token = async_mock.CoroutineMock(
                return_value="test_token"
            )

            await test_module.wallet_create_token(self.request)

            self.mock_multitenant_mgr.create_auth_token.assert_called_once_with(
                mock_wallet_record, None
            )
            mock_response.assert_called_once_with({"token": "test_token"})

    async def test_wallet_create_token_unmanaged(self):
        self.request.match_info = {"wallet_id": "dummy"}
        self.request.json = async_mock.CoroutineMock(
            return_value={"wallet_key": "dummy_key"}
        )
        mock_wallet_record = async_mock.MagicMock()
        mock_wallet_record.serialize = async_mock.MagicMock(
            return_value={"settings": {}, "wallet_id": "dummy"}
        )

        with async_mock.patch.object(
            test_module.WalletRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_wallet_record_retrieve_by_id, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_wallet_record_retrieve_by_id.return_value = mock_wallet_record

            self.mock_multitenant_mgr.create_auth_token = async_mock.CoroutineMock(
                return_value="test_token"
            )

            await test_module.wallet_create_token(self.request)

            self.mock_multitenant_mgr.create_auth_token.assert_called_once_with(
                mock_wallet_record, "dummy_key"
            )
            mock_response.assert_called_once_with({"token": "test_token"})

    async def test_wallet_create_token_managed_wallet_key_provided_throws(self):
        self.request.match_info = {"wallet_id": "dummy"}
        self.request.json = async_mock.CoroutineMock(
            return_value={"wallet_key": "dummy_key"}
        )
        mock_wallet_record = async_mock.MagicMock()
        mock_wallet_record.serialize = async_mock.MagicMock(
            return_value={"settings": {}, "wallet_id": "dummy"}
        )
        mock_wallet_record.requires_external_key = False

        with async_mock.patch.object(
            test_module.WalletRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_wallet_record_retrieve_by_id:
            mock_wallet_record_retrieve_by_id.return_value = mock_wallet_record

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.wallet_create_token(self.request)

    async def test_wallet_create_token_x(self):
        self.request.has_body = False
        self.request.match_info = {"wallet_id": "dummy"}

        with async_mock.patch.object(
            test_module.WalletRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_wallet_record_retrieve_by_id:
            mock_wallet_record_retrieve_by_id.return_value = async_mock.MagicMock()

            with self.assertRaises(test_module.web.HTTPUnauthorized):
                mock_wallet_record_retrieve_by_id.side_effect = (
                    test_module.WalletKeyMissingError()
                )
                await test_module.wallet_create_token(self.request)

            with self.assertRaises(test_module.web.HTTPNotFound):
                mock_wallet_record_retrieve_by_id.side_effect = (
                    test_module.StorageNotFoundError()
                )
                await test_module.wallet_create_token(self.request)

    async def test_wallet_remove_managed(self):
        self.request.has_body = False
        self.request.match_info = {"wallet_id": "dummy"}

        with async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response, async_mock.patch.object(
            test_module.WalletRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ):
            self.mock_multitenant_mgr.remove_wallet = async_mock.CoroutineMock()

            await test_module.wallet_remove(self.request)

            self.mock_multitenant_mgr.remove_wallet.assert_called_once_with(
                "dummy", None
            )
            mock_response.assert_called_once_with({})

    async def test_wallet_remove_unmanaged(self):
        self.request.match_info = {"wallet_id": "dummy"}
        self.request.json = async_mock.CoroutineMock(
            return_value={"wallet_key": "dummy_key"}
        )

        with async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response, async_mock.patch.object(
            test_module.WalletRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ):
            self.mock_multitenant_mgr.remove_wallet = async_mock.CoroutineMock()

            await test_module.wallet_remove(self.request)

            self.mock_multitenant_mgr.remove_wallet.assert_called_once_with(
                "dummy", "dummy_key"
            )
            mock_response.assert_called_once_with({})

    async def test_wallet_remove_managed_wallet_key_provided_throws(self):
        self.request.match_info = {"wallet_id": "dummy"}
        self.request.json = async_mock.CoroutineMock(
            return_value={"wallet_key": "dummy_key"}
        )

        mock_wallet_record = async_mock.MagicMock()
        mock_wallet_record.requires_external_key = False

        with async_mock.patch.object(
            test_module.WalletRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_wallet_record_retrieve_by_id:
            mock_wallet_record_retrieve_by_id.return_value = mock_wallet_record

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.wallet_remove(self.request)

    async def test_wallet_remove_x(self):
        self.request.has_body = False
        self.request.match_info = {"wallet_id": "dummy"}

        self.mock_multitenant_mgr.remove_wallet = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module.WalletRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ):
            with self.assertRaises(test_module.web.HTTPUnauthorized):
                self.mock_multitenant_mgr.remove_wallet.side_effect = (
                    test_module.WalletKeyMissingError()
                )
                await test_module.wallet_remove(self.request)

            with self.assertRaises(test_module.web.HTTPNotFound):
                self.mock_multitenant_mgr.remove_wallet.side_effect = (
                    test_module.StorageNotFoundError()
                )
                await test_module.wallet_remove(self.request)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
