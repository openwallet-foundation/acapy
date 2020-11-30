import json
import pytest

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from aiohttp.web import HTTPForbidden

from ...config.injector import Injector
from ...config.injection_context import InjectionContext
from ...core.profile import Profile, ProfileSession
from ...indy.holder import IndyHolder
from ...ledger.base import BaseLedger
from ...ledger.error import LedgerError
from ...messaging.request_context import RequestContext
from ...wallet.base import BaseWallet

from .. import routes as test_module


class TestHolderRoutes(AsyncTestCase):
    def setUp(self):
        self.profile = async_mock.MagicMock(Profile)()
        self.session = async_mock.MagicMock(ProfileSession)()
        self.profile.session = async_mock.CoroutineMock(return_value=self.session)
        self.injector = Injector(enforce_typing=False)

        def inject(cls, required=True):
            return self.injector.inject(cls, required=required)

        self.session.inject = inject

        self.context = RequestContext(self.profile)

        self.app = {
            "request_context": self.context,
        }

    async def test_credentials_get(self):
        request = async_mock.MagicMock(
            app=self.app, match_info={"credential_id": "dummy"}
        )

        self.injector.bind_instance(
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
            result = await test_module.credentials_get(request)
            json_response.assert_called_once_with({"hello": "world"})
            assert result is json_response.return_value

    async def test_credentials_get_not_found(self):
        request = async_mock.MagicMock(
            app=self.app, match_info={"credential_id": "dummy"}
        )
        self.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credential=async_mock.CoroutineMock(
                    side_effect=test_module.WalletNotFoundError()
                )
            ),
        )
        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.credentials_get(request)

    async def test_credentials_revoked(self):
        request = async_mock.MagicMock(
            app=self.app,
            match_info={"credential_id": "dummy"},
            query={},
        )

        ledger = async_mock.create_autospec(BaseLedger)
        self.injector.bind_instance(BaseLedger, ledger)
        self.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                credential_revoked=async_mock.CoroutineMock(return_value=False)
            ),
        )

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            result = await test_module.credentials_revoked(request)
            json_response.assert_called_once_with({"revoked": False})
            assert result is json_response.return_value

    async def test_credentials_revoked_no_ledger(self):
        request = async_mock.MagicMock(
            app=self.app,
            match_info={"credential_id": "dummy"},
            query={},
        )

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.credentials_revoked(request)

    async def test_credentials_not_found(self):
        request = async_mock.MagicMock(
            app=self.app, match_info={"credential_id": "dummy"}
        )
        ledger = async_mock.create_autospec(BaseLedger)
        self.injector.bind_instance(BaseLedger, ledger)
        self.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                credential_revoked=async_mock.CoroutineMock(
                    side_effect=test_module.WalletNotFoundError("no such cred")
                )
            ),
        )

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.credentials_revoked(request)

    async def test_credentials_x_ledger(self):
        request = async_mock.MagicMock(
            app=self.app, match_info={"credential_id": "dummy"}
        )
        ledger = async_mock.create_autospec(BaseLedger)
        self.injector.bind_instance(BaseLedger, ledger)
        self.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                credential_revoked=async_mock.CoroutineMock(
                    side_effect=test_module.LedgerError("down for maintenance")
                )
            ),
        )

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credentials_revoked(request)

    async def test_attribute_mime_types_get(self):
        request = async_mock.MagicMock(
            app=self.app, match_info={"credential_id": "dummy"}
        )

        self.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_mime_type=async_mock.CoroutineMock(return_value=None)
            ),
        )

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            await test_module.credentials_attr_mime_types_get(request)
            mock_response.assert_called_once_with(None)

    async def test_credentials_remove(self):
        request = async_mock.MagicMock(
            app=self.app, match_info={"credential_id": "dummy"}
        )

        self.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                delete_credential=async_mock.CoroutineMock(return_value=None)
            ),
        )

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            result = await test_module.credentials_remove(request)
            json_response.assert_called_once_with({})
            assert result is json_response.return_value

    async def test_credentials_remove_not_found(self):
        request = async_mock.MagicMock(
            app=self.app, match_info={"credential_id": "dummy"}
        )

        self.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                delete_credential=async_mock.CoroutineMock(
                    side_effect=test_module.WalletNotFoundError()
                )
            ),
        )
        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.credentials_remove(request)

    async def test_credentials_list(self):
        request = async_mock.MagicMock(
            app=self.app, query={"start": "0", "count": "10"}
        )

        self.injector.bind_instance(
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
            result = await test_module.credentials_list(request)
            json_response.assert_called_once_with({"results": {"hello": "world"}})
            assert result is json_response.return_value

    async def test_credentials_list_x_holder(self):
        request = async_mock.MagicMock(
            app=self.app, query={"start": "0", "count": "10"}
        )

        self.injector.bind_instance(
            IndyHolder,
            async_mock.MagicMock(
                get_credentials=async_mock.CoroutineMock(
                    side_effect=test_module.IndyHolderError()
                )
            ),
        )

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credentials_list(request)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
