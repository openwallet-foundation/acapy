import json

from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ...config.injection_context import InjectionContext
from ...ledger.base import BaseLedger
from ...wallet.base import BaseWallet

from ...admin.request_context import AdminRequestContext
from ...indy.holder import IndyHolder
from ...ledger.base import BaseLedger

from .. import routes as test_module


class TestHolderRoutes(AsyncTestCase):
    def setUp(self):
        self.context = AdminRequestContext.test_context()

        self.request_dict = {"context": self.context}
        self.request = async_mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
        )

    async def test_credentials_get(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credential=async_mock.CoroutineMock(
                    return_value=json.dumps({"hello": "world"})
                )
            ),
        )

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            result = await test_module.credentials_get(self.request)
            json_response.assert_called_once_with({"hello": "world"})
            assert result is json_response.return_value

    async def test_credentials_get_not_found(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credential=async_mock.CoroutineMock(
                    side_effect=test_module.WalletNotFoundError()
                )
            ),
        )

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.credentials_get(self.request)

    async def test_credentials_revoked(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.context.injector.bind_instance(
            BaseLedger, async_mock.create_autospec(BaseLedger)
        )
        self.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                credential_revoked=async_mock.CoroutineMock(return_value=False)
            ),
        )

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            result = await test_module.credentials_revoked(self.request)
            json_response.assert_called_once_with({"revoked": False})
            assert result is json_response.return_value

    async def test_credentials_revoked_no_ledger(self):
        self.request.match_info = {"credential_id": "dummy"}

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.credentials_revoked(self.request)

    async def test_credentials_not_found(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.context.injector.bind_instance(
            BaseLedger, async_mock.create_autospec(BaseLedger)
        )
        self.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                credential_revoked=async_mock.CoroutineMock(
                    side_effect=test_module.WalletNotFoundError("no such cred")
                )
            ),
        )

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.credentials_revoked(self.request)

    async def test_credentials_x_ledger(self):
        self.request.match_info = {"credential_id": "dummy"}
        ledger = async_mock.create_autospec(BaseLedger)
        self.context.injector.bind_instance(
            BaseLedger, async_mock.create_autospec(BaseLedger)
        )
        self.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                credential_revoked=async_mock.CoroutineMock(
                    side_effect=test_module.LedgerError("down for maintenance")
                )
            ),
        )

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credentials_revoked(self.request)

    async def test_attribute_mime_types_get(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_mime_type=async_mock.CoroutineMock(return_value=None)
            ),
        )

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            await test_module.credentials_attr_mime_types_get(self.request)
            mock_response.assert_called_once_with(None)

    async def test_credentials_remove(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                delete_credential=async_mock.CoroutineMock(return_value=None)
            ),
        )

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            result = await test_module.credentials_remove(self.request)
            json_response.assert_called_once_with({})
            assert result is json_response.return_value

    async def test_credentials_remove_not_found(self):
        self.request.match_info = {"credential_id": "dummy"}
        self.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                delete_credential=async_mock.CoroutineMock(
                    side_effect=test_module.WalletNotFoundError()
                )
            ),
        )
        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.credentials_remove(self.request)

    async def test_credentials_list(self):
        self.request.query = {"start": "0", "count": "10"}
        self.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials=async_mock.CoroutineMock(
                    return_value={"hello": "world"}
                )
            ),
        )

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            result = await test_module.credentials_list(self.request)
            json_response.assert_called_once_with({"results": {"hello": "world"}})
            assert result is json_response.return_value

    async def test_credentials_list_x_holder(self):
        self.request.query = {"start": "0", "count": "10"}
        self.context.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials=async_mock.CoroutineMock(
                    side_effect=test_module.IndyHolderError()
                )
            ),
        )

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credentials_list(self.request)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
