from unittest import IsolatedAsyncioTestCase

from marshmallow.exceptions import ValidationError

from ....admin.request_context import AdminRequestContext
from ....messaging.models.base import BaseModelError
from ....storage.error import StorageError, StorageNotFoundError
from ....tests import mock
from ....utils.testing import create_test_profile
from ....wallet.models.wallet_record import WalletRecord
from ...base import BaseMultitenantManager
from ...error import MultitenantManagerError
from .. import routes as test_module


class TestMultitenantRoutes(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = await create_test_profile(
            settings={"wallet.type": "askar", "admin.admin_api_key": "secret-key"},
        )
        self.context = AdminRequestContext.test_context({}, self.profile)
        self.request_dict = {
            "context": self.context,
        }

        self.request_dict = {
            "context": self.context,
            "outbound_message_router": mock.CoroutineMock(),
        }
        self.request = mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
            headers={"x-api-key": "secret-key"},
        )

    async def test_format_wallet_record_removes_wallet_key(self):
        wallet_record = WalletRecord(
            wallet_id="test",
            key_management_mode=WalletRecord.MODE_MANAGED,
            settings={
                "wallet.name": "wallet_name",
                "wallet.key": "wallet_key",
                "admin.admin_api_key": "secret-key",
            },
        )

        formatted = test_module.format_wallet_record(wallet_record)

        assert "wallet.key" not in formatted["settings"]

    async def test_wallets_list(self):
        with (
            mock.patch.object(
                test_module, "WalletRecord", autospec=True
            ) as mock_wallet_record,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            wallets = [
                mock.MagicMock(
                    serialize=mock.MagicMock(
                        return_value={
                            "wallet_id": "wallet_id",
                            "created_at": "1234567890",
                            "settings": {"wallet.name": "test"},
                        }
                    )
                ),
                mock.MagicMock(
                    serialize=mock.MagicMock(
                        return_value={
                            "wallet_id": "wallet_id",
                            "created_at": "1234567891",
                            "settings": {"wallet.name": "test"},
                        }
                    )
                ),
                mock.MagicMock(
                    serialize=mock.MagicMock(
                        return_value={
                            "wallet_id": "wallet_id",
                            "created_at": "1234567892",
                            "settings": {"wallet.name": "test"},
                        }
                    )
                ),
            ]
            mock_wallet_record.query = mock.CoroutineMock()
            mock_wallet_record.query.return_value = wallets

            await test_module.wallets_list(self.request)
            mock_response.assert_called_once_with(
                {"results": [test_module.format_wallet_record(w) for w in wallets]}
            )

    async def test_wallets_list_x(self):
        with mock.patch.object(
            test_module, "WalletRecord", autospec=True
        ) as mock_wallet_record:
            mock_wallet_record.query = mock.CoroutineMock()

            mock_wallet_record.query.side_effect = StorageError()
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.wallets_list(self.request)

            mock_wallet_record.query.side_effect = BaseModelError()
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.wallets_list(self.request)

    async def test_wallets_list_query(self):
        self.request.query = {"wallet_name": "test"}

        with (
            mock.patch.object(
                test_module, "WalletRecord", autospec=True
            ) as mock_wallet_record,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            wallets = [
                mock.MagicMock(
                    serialize=mock.MagicMock(
                        return_value={
                            "wallet_id": "wallet_id",
                            "created_at": "1234567890",
                            "settings": {"wallet.name": "test"},
                        }
                    )
                ),
            ]
            mock_wallet_record.query = mock.CoroutineMock()
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

    async def test_wallet_create_tenant_settings(self):
        body = {
            "wallet_name": "test",
            "default_label": "test_label",
            "wallet_type": "askar",
            "wallet_key": "test",
            "key_management_mode": "managed",
            "wallet_webhook_urls": [],
            "wallet_dispatch_type": "base",
            "extra_settings": {
                "ACAPY_LOG_LEVEL": "INFO",
                "ACAPY_INVITE_PUBLIC": True,
                "ACAPY_PUBLIC_INVITES": True,
            },
        }
        self.request.json = mock.CoroutineMock(return_value=body)

        test_module.attempt_auto_author_with_endorser_setup = mock.CoroutineMock()

        with mock.patch.object(test_module.web, "json_response") as mock_response:
            wallet_mock = mock.MagicMock(
                serialize=mock.MagicMock(
                    return_value={
                        "wallet_id": "test",
                        "settings": {},
                        "key_management_mode": body["key_management_mode"],
                    }
                )
            )  # wallet_record
            mock_multitenant_mgr = mock.AsyncMock(BaseMultitenantManager, autospec=True)
            mock_multitenant_mgr.create_auth_token = mock.CoroutineMock(
                return_value="test_token"
            )
            mock_multitenant_mgr.create_wallet = mock.CoroutineMock(
                return_value=wallet_mock
            )

            mock_multitenant_mgr.create_auth_token = mock.CoroutineMock(
                return_value="test_token"
            )
            mock_multitenant_mgr.get_wallet_profile = mock.CoroutineMock(
                return_value=mock.MagicMock()
            )
            self.profile.context.injector.bind_instance(
                BaseMultitenantManager, mock_multitenant_mgr
            )

            await test_module.wallet_create(self.request)

            mock_multitenant_mgr.create_wallet.assert_called_once_with(
                {
                    "wallet.type": body["wallet_type"],
                    "wallet.name": body["wallet_name"],
                    "wallet.key": body["wallet_key"],
                    "dbstore.key": body.get("dbstore_key"),
                    "wallet.webhook_urls": body["wallet_webhook_urls"],
                    "wallet.dispatch_type": body["wallet_dispatch_type"],
                    "log.level": "INFO",
                    "debug.invite_public": True,
                    "public_invites": True,
                },
                body["key_management_mode"],
            )
            mock_multitenant_mgr.create_auth_token.assert_called_once_with(
                wallet_mock, body["wallet_key"]
            )
            mock_response.assert_called_once_with(
                {**test_module.format_wallet_record(wallet_mock), "token": "test_token"}
            )
            assert mock_multitenant_mgr.get_wallet_profile.called
            assert test_module.attempt_auto_author_with_endorser_setup.called

    async def test_wallet_create(self):
        body = {
            "wallet_name": "test",
            "default_label": "test_label",
            "wallet_type": "askar",
            "wallet_key": "test",
            "key_management_mode": "managed",
            "wallet_webhook_urls": [],
            "wallet_dispatch_type": "base",
        }
        self.request.json = mock.CoroutineMock(return_value=body)
        test_module.attempt_auto_author_with_endorser_setup = mock.CoroutineMock()

        with mock.patch.object(test_module.web, "json_response") as mock_response:
            wallet_mock = mock.MagicMock(
                serialize=mock.MagicMock(
                    return_value={
                        "wallet_id": "test",
                        "settings": {},
                        "key_management_mode": body["key_management_mode"],
                    }
                )
            )  # wallet_record
            mock_multitenant_mgr = mock.AsyncMock(BaseMultitenantManager, autospec=True)
            mock_multitenant_mgr.create_wallet = mock.CoroutineMock(
                return_value=wallet_mock
            )

            mock_multitenant_mgr.create_auth_token = mock.CoroutineMock(
                return_value="test_token"
            )
            mock_multitenant_mgr.get_wallet_profile = mock.CoroutineMock(
                return_value=mock.MagicMock()
            )
            self.profile.context.injector.bind_instance(
                BaseMultitenantManager, mock_multitenant_mgr
            )

            await test_module.wallet_create(self.request)

            mock_multitenant_mgr.create_wallet.assert_called_once_with(
                {
                    "wallet.type": body["wallet_type"],
                    "wallet.name": body["wallet_name"],
                    "wallet.key": body["wallet_key"],
                    "dbstore.key": body.get("dbstore_key"),
                    "wallet.webhook_urls": body["wallet_webhook_urls"],
                    "wallet.dispatch_type": body["wallet_dispatch_type"],
                },
                body["key_management_mode"],
            )
            mock_multitenant_mgr.create_auth_token.assert_called_once_with(
                wallet_mock, body["wallet_key"]
            )
            mock_response.assert_called_once_with(
                {
                    **test_module.format_wallet_record(wallet_mock),
                    "token": "test_token",
                }
            )
            assert mock_multitenant_mgr.get_wallet_profile.called
            assert test_module.attempt_auto_author_with_endorser_setup.called

    async def test_wallet_create_x(self):
        body = {}
        self.request.json = mock.CoroutineMock(return_value=body)
        mock_multitenant_mgr = mock.AsyncMock(BaseMultitenantManager, autospec=True)
        mock_multitenant_mgr.create_wallet.side_effect = MultitenantManagerError()
        self.profile.context.injector.bind_instance(
            BaseMultitenantManager, mock_multitenant_mgr
        )

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
        self.request.json = mock.CoroutineMock(return_value=body)
        test_module.attempt_auto_author_with_endorser_setup = mock.CoroutineMock()

        with mock.patch.object(test_module.web, "json_response"):
            mock_multitenant_mgr = mock.AsyncMock(BaseMultitenantManager, autospec=True)
            mock_multitenant_mgr.create_wallet = mock.CoroutineMock(
                return_value=mock.MagicMock()
            )
            mock_multitenant_mgr.create_auth_token = mock.CoroutineMock()
            mock_multitenant_mgr.get_wallet_profile = mock.CoroutineMock(
                return_value=mock.MagicMock()
            )

            self.profile.context.injector.bind_instance(
                BaseMultitenantManager, mock_multitenant_mgr
            )

            await test_module.wallet_create(self.request)
            mock_multitenant_mgr.create_wallet.assert_called_once_with(
                {
                    "wallet.type": "askar",
                    "wallet.name": body["wallet_name"],
                    "wallet.key": body["wallet_key"],
                    "dbstore.key": body.get("dbstore_key"),
                    "default_label": body["label"],
                    "image_url": body["image_url"],
                    "wallet.webhook_urls": body["wallet_webhook_urls"],
                    "wallet.dispatch_type": body["wallet_dispatch_type"],
                    "wallet.key_derivation_method": body["wallet_key_derivation"],
                },
                WalletRecord.MODE_MANAGED,
            )
            assert mock_multitenant_mgr.get_wallet_profile.called
            assert test_module.attempt_auto_author_with_endorser_setup.called

    async def test_wallet_create_raw_key_derivation(self):
        body = {
            "wallet_name": "test",
            "wallet_key": "test",
            "wallet_key_derivation": "RAW",
        }
        self.request.json = mock.CoroutineMock(return_value=body)
        test_module.attempt_auto_author_with_endorser_setup = mock.CoroutineMock()

        with mock.patch.object(test_module.web, "json_response"):
            mock_multitenant_mgr = mock.AsyncMock(BaseMultitenantManager, autospec=True)
            mock_multitenant_mgr.create_wallet = mock.CoroutineMock(
                return_value=mock.MagicMock()
            )
            mock_multitenant_mgr.create_auth_token = mock.CoroutineMock()
            mock_multitenant_mgr.get_wallet_profile = mock.CoroutineMock(
                return_value=mock.MagicMock()
            )

            self.profile.context.injector.bind_instance(
                BaseMultitenantManager, mock_multitenant_mgr
            )

            await test_module.wallet_create(self.request)
            mock_multitenant_mgr.create_wallet.assert_called_once_with(
                {
                    "wallet.type": "askar",
                    "wallet.name": body["wallet_name"],
                    "wallet.key": body["wallet_key"],
                    "dbstore.key": body.get("dbstore_key"),
                    "wallet.key_derivation_method": body["wallet_key_derivation"],
                    "wallet.webhook_urls": [],
                    "wallet.dispatch_type": "base",
                },
                WalletRecord.MODE_MANAGED,
            )
            assert mock_multitenant_mgr.get_wallet_profile.called
            assert test_module.attempt_auto_author_with_endorser_setup.called

    async def test_wallet_update_tenant_settings(self):
        self.request.match_info = {"wallet_id": "test-wallet-id"}
        body = {
            "wallet_webhook_urls": ["test-webhook-url"],
            "wallet_dispatch_type": "default",
            "label": "test-label",
            "image_url": "test-image-url",
            "extra_settings": {
                "ACAPY_LOG_LEVEL": "INFO",
                "ACAPY_INVITE_PUBLIC": True,
                "ACAPY_PUBLIC_INVITES": True,
            },
        }
        self.request.json = mock.CoroutineMock(return_value=body)

        with mock.patch.object(test_module.web, "json_response") as mock_response:
            settings = {
                "wallet.webhook_urls": body["wallet_webhook_urls"],
                "wallet.dispatch_type": body["wallet_dispatch_type"],
                "default_label": body["label"],
                "image_url": body["image_url"],
                "log.level": "INFO",
                "debug.invite_public": True,
                "public_invites": True,
            }
            wallet_mock = mock.MagicMock(
                serialize=mock.MagicMock(
                    return_value={
                        "wallet_id": "test-wallet-id",
                        "settings": settings,
                    }
                )
            )
            mock_multitenant_mgr = mock.AsyncMock(BaseMultitenantManager, autospec=True)
            mock_multitenant_mgr.update_wallet = mock.CoroutineMock(
                return_value=wallet_mock
            )

            self.profile.context.injector.bind_instance(
                BaseMultitenantManager, mock_multitenant_mgr
            )

            await test_module.wallet_update(self.request)

            mock_multitenant_mgr.update_wallet.assert_called_once_with(
                "test-wallet-id",
                settings,
            )
            mock_response.assert_called_once_with(
                {"wallet_id": "test-wallet-id", "settings": settings}
            )

    async def test_wallet_update(self):
        self.request.match_info = {"wallet_id": "test-wallet-id"}
        body = {
            "wallet_webhook_urls": ["test-webhook-url"],
            "wallet_dispatch_type": "default",
            "label": "test-label",
            "image_url": "test-image-url",
        }
        self.request.json = mock.CoroutineMock(return_value=body)

        with mock.patch.object(test_module.web, "json_response") as mock_response:
            settings = {
                "wallet.webhook_urls": body["wallet_webhook_urls"],
                "wallet.dispatch_type": body["wallet_dispatch_type"],
                "default_label": body["label"],
                "image_url": body["image_url"],
            }
            wallet_mock = mock.MagicMock(
                serialize=mock.MagicMock(
                    return_value={
                        "wallet_id": "test-wallet-id",
                        "settings": settings,
                    }
                )
            )
            mock_multitenant_mgr = mock.AsyncMock(BaseMultitenantManager, autospec=True)
            mock_multitenant_mgr.update_wallet = mock.CoroutineMock(
                return_value=wallet_mock
            )

            self.profile.context.injector.bind_instance(
                BaseMultitenantManager, mock_multitenant_mgr
            )

            await test_module.wallet_update(self.request)

            mock_multitenant_mgr.update_wallet.assert_called_once_with(
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
        self.request.json = mock.CoroutineMock(return_value=body)

        with mock.patch.object(test_module.web, "json_response") as mock_response:
            settings = {
                "default_label": body["label"],
                "image_url": body["image_url"],
            }
            wallet_mock = mock.MagicMock(
                serialize=mock.MagicMock(
                    return_value={
                        "wallet_id": "test-wallet-id",
                        "settings": settings,
                    }
                )
            )
            mock_multitenant_mgr = mock.AsyncMock(BaseMultitenantManager, autospec=True)
            mock_multitenant_mgr.update_wallet = mock.CoroutineMock(
                return_value=wallet_mock
            )

            self.profile.context.injector.bind_instance(
                BaseMultitenantManager, mock_multitenant_mgr
            )

            await test_module.wallet_update(self.request)

            mock_multitenant_mgr.update_wallet.assert_called_once_with(
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
        self.request.json = mock.CoroutineMock(return_value=body)

        with mock.patch.object(test_module.web, "json_response") as mock_response:
            settings = {
                "wallet.webhook_urls": [],
                "wallet.dispatch_type": "base",
                "default_label": body["label"],
                "image_url": body["image_url"],
            }
            wallet_mock = mock.MagicMock(
                serialize=mock.MagicMock(
                    return_value={
                        "wallet_id": "test-wallet-id",
                        "settings": settings,
                    }
                )
            )
            mock_multitenant_mgr = mock.AsyncMock(BaseMultitenantManager, autospec=True)
            mock_multitenant_mgr.update_wallet = mock.CoroutineMock(
                return_value=wallet_mock
            )

            self.profile.context.injector.bind_instance(
                BaseMultitenantManager, mock_multitenant_mgr
            )

            await test_module.wallet_update(self.request)

            mock_multitenant_mgr.update_wallet.assert_called_once_with(
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
        self.request.json = mock.CoroutineMock(return_value=body)

        with mock.patch.object(test_module.web, "json_response"):
            mock_multitenant_mgr = mock.AsyncMock(BaseMultitenantManager, autospec=True)
            mock_multitenant_mgr.update_wallet = mock.CoroutineMock(
                side_effect=test_module.WalletSettingsError("bad settings")
            )

            self.profile.context.injector.bind_instance(
                BaseMultitenantManager, mock_multitenant_mgr
            )

            with self.assertRaises(test_module.web.HTTPBadRequest) as context:
                await test_module.wallet_update(self.request)
            assert "bad settings" in str(context.exception)

    async def test_wallet_update_no_params(self):
        self.request.match_info = {"wallet_id": "test-wallet-id"}
        body = {}
        self.request.json = mock.CoroutineMock(return_value=body)

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_update(self.request)

    async def test_wallet_update_not_found(self):
        self.request.match_info = {"wallet_id": "test-wallet-id"}
        body = {"label": "test-label"}
        self.request.json = mock.CoroutineMock(return_value=body)
        mock_multitenant_mgr = mock.AsyncMock(BaseMultitenantManager, autospec=True)
        mock_multitenant_mgr.update_wallet = mock.CoroutineMock(
            side_effect=StorageNotFoundError()
        )
        self.profile.context.injector.bind_instance(
            BaseMultitenantManager, mock_multitenant_mgr
        )

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.wallet_update(self.request)

    async def test_wallet_get(self):
        self.request.match_info = {"wallet_id": "dummy"}
        mock_wallet_record = mock.MagicMock()
        mock_wallet_record.serialize = mock.MagicMock(
            return_value={"settings": {}, "wallet_id": "dummy"}
        )

        with (
            mock.patch.object(
                test_module.WalletRecord, "retrieve_by_id", mock.CoroutineMock()
            ) as mock_wallet_record_retrieve_by_id,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_wallet_record_retrieve_by_id.return_value = mock_wallet_record

            await test_module.wallet_get(self.request)
            mock_response.assert_called_once_with({"settings": {}, "wallet_id": "dummy"})

    async def test_wallet_get_not_found(self):
        self.request.match_info = {"wallet_id": "dummy"}

        with mock.patch.object(
            test_module.WalletRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_wallet_record_retrieve_by_id:
            mock_wallet_record_retrieve_by_id.side_effect = StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.wallet_get(self.request)

    async def test_wallet_get_x(self):
        self.request.match_info = {"wallet_id": "dummy"}
        mock_wallet_record = mock.MagicMock()
        mock_wallet_record.serialize = mock.MagicMock(
            side_effect=test_module.BaseModelError()
        )

        with mock.patch.object(
            test_module.WalletRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_wallet_record_retrieve_by_id:
            mock_wallet_record_retrieve_by_id.return_value = mock_wallet_record

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.wallet_get(self.request)

    async def test_wallet_create_token_managed(self):
        self.request.has_body = False
        self.request.match_info = {"wallet_id": "dummy"}
        mock_wallet_record = mock.MagicMock()
        mock_wallet_record.serialize = mock.MagicMock(
            return_value={"settings": {}, "wallet_id": "dummy"}
        )

        with (
            mock.patch.object(
                test_module.WalletRecord, "retrieve_by_id", mock.CoroutineMock()
            ) as mock_wallet_record_retrieve_by_id,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_wallet_record_retrieve_by_id.return_value = mock_wallet_record
            mock_multitenant_mgr = mock.AsyncMock(BaseMultitenantManager, autospec=True)
            mock_multitenant_mgr.create_auth_token = mock.CoroutineMock(
                return_value="test_token"
            )
            self.profile.context.injector.bind_instance(
                BaseMultitenantManager, mock_multitenant_mgr
            )

            await test_module.wallet_create_token(self.request)

            mock_multitenant_mgr.create_auth_token.assert_called_once_with(
                mock_wallet_record, None
            )
            mock_response.assert_called_once_with({"token": "test_token"})

    async def test_wallet_create_token_unmanaged(self):
        self.request.match_info = {"wallet_id": "dummy"}
        self.request.json = mock.CoroutineMock(return_value={"wallet_key": "dummy_key"})
        mock_wallet_record = mock.MagicMock()
        mock_wallet_record.serialize = mock.MagicMock(
            return_value={"settings": {}, "wallet_id": "dummy"}
        )

        with (
            mock.patch.object(
                test_module.WalletRecord, "retrieve_by_id", mock.CoroutineMock()
            ) as mock_wallet_record_retrieve_by_id,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_wallet_record_retrieve_by_id.return_value = mock_wallet_record
            mock_multitenant_mgr = mock.AsyncMock(BaseMultitenantManager, autospec=True)
            mock_multitenant_mgr.create_auth_token = mock.CoroutineMock(
                return_value="test_token"
            )
            self.profile.context.injector.bind_instance(
                BaseMultitenantManager, mock_multitenant_mgr
            )

            await test_module.wallet_create_token(self.request)

            mock_multitenant_mgr.create_auth_token.assert_called_once_with(
                mock_wallet_record, "dummy_key"
            )
            mock_response.assert_called_once_with({"token": "test_token"})

    async def test_wallet_create_token_managed_wallet_key_provided_throws(self):
        self.request.match_info = {"wallet_id": "dummy"}
        self.request.json = mock.CoroutineMock(return_value={"wallet_key": "dummy_key"})
        mock_multitenant_mgr = mock.AsyncMock(BaseMultitenantManager, autospec=True)
        self.profile.context.injector.bind_instance(
            BaseMultitenantManager, mock_multitenant_mgr
        )
        mock_wallet_record = mock.MagicMock()
        mock_wallet_record.serialize = mock.MagicMock(
            return_value={"settings": {}, "wallet_id": "dummy"}
        )
        mock_wallet_record.requires_external_key = False

        with mock.patch.object(
            test_module.WalletRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_wallet_record_retrieve_by_id:
            mock_wallet_record_retrieve_by_id.return_value = mock_wallet_record

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.wallet_create_token(self.request)

    async def test_wallet_create_token_x(self):
        self.request.has_body = False
        self.request.match_info = {"wallet_id": "dummy"}
        mock_multitenant_mgr = mock.AsyncMock(BaseMultitenantManager, autospec=True)
        self.profile.context.injector.bind_instance(
            BaseMultitenantManager, mock_multitenant_mgr
        )

        with mock.patch.object(
            test_module.WalletRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_wallet_record_retrieve_by_id:
            mock_wallet_record_retrieve_by_id.return_value = mock.MagicMock()

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
        mock_multitenant_mgr = mock.AsyncMock(BaseMultitenantManager, autospec=True)
        mock_multitenant_mgr.remove_wallet = mock.CoroutineMock()
        self.profile.context.injector.bind_instance(
            BaseMultitenantManager, mock_multitenant_mgr
        )

        with (
            mock.patch.object(test_module.web, "json_response") as mock_response,
            mock.patch.object(
                test_module.WalletRecord, "retrieve_by_id", mock.CoroutineMock()
            ),
        ):
            result = await test_module.wallet_remove(self.request)

            mock_multitenant_mgr.remove_wallet.assert_called_once_with("dummy", None)
            mock_response.assert_called_once_with({})
            assert result == mock_response.return_value

    async def test_wallet_remove_unmanaged(self):
        self.request.match_info = {"wallet_id": "dummy"}
        self.request.json = mock.CoroutineMock(return_value={"wallet_key": "dummy_key"})
        mock_multitenant_mgr = mock.AsyncMock(BaseMultitenantManager, autospec=True)
        mock_multitenant_mgr.remove_wallet = mock.CoroutineMock()
        self.profile.context.injector.bind_instance(
            BaseMultitenantManager, mock_multitenant_mgr
        )
        with (
            mock.patch.object(test_module.web, "json_response") as mock_response,
            mock.patch.object(
                test_module.WalletRecord, "retrieve_by_id", mock.CoroutineMock()
            ),
        ):
            result = await test_module.wallet_remove(self.request)

            mock_multitenant_mgr.remove_wallet.assert_called_once_with(
                "dummy", "dummy_key"
            )
            mock_response.assert_called_once_with({})
            assert result == mock_response.return_value

    async def test_wallet_remove_managed_wallet_key_provided_throws(self):
        self.request.match_info = {"wallet_id": "dummy"}
        self.request.json = mock.CoroutineMock(return_value={"wallet_key": "dummy_key"})

        mock_wallet_record = mock.MagicMock()
        mock_wallet_record.requires_external_key = False
        mock_multitenant_mgr = mock.AsyncMock(BaseMultitenantManager, autospec=True)
        self.profile.context.injector.bind_instance(
            BaseMultitenantManager, mock_multitenant_mgr
        )

        with mock.patch.object(
            test_module.WalletRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_wallet_record_retrieve_by_id:
            mock_wallet_record_retrieve_by_id.return_value = mock_wallet_record

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.wallet_remove(self.request)

    async def test_wallet_remove_x(self):
        self.request.has_body = False
        self.request.match_info = {"wallet_id": "dummy"}

        with mock.patch.object(
            test_module.WalletRecord, "retrieve_by_id", mock.CoroutineMock()
        ):
            mock_multitenant_mgr = mock.AsyncMock(BaseMultitenantManager, autospec=True)
            mock_multitenant_mgr.remove_wallet = mock.CoroutineMock()
            self.profile.context.injector.bind_instance(
                BaseMultitenantManager, mock_multitenant_mgr
            )
            with self.assertRaises(test_module.web.HTTPUnauthorized):
                mock_multitenant_mgr.remove_wallet.side_effect = (
                    test_module.WalletKeyMissingError()
                )
                await test_module.wallet_remove(self.request)

            with self.assertRaises(test_module.web.HTTPNotFound):
                mock_multitenant_mgr.remove_wallet.side_effect = (
                    test_module.StorageNotFoundError()
                )
                await test_module.wallet_remove(self.request)

    async def test_register(self):
        mock_app = mock.MagicMock()
        mock_app.add_routes = mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
