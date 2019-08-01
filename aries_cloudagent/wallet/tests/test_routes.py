from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
import pytest

from aiohttp.web import HTTPForbidden

from ...config.injection_context import InjectionContext
from ...wallet.base import BaseWallet, DIDInfo

from .. import routes as test_module


class TestWalletRoutes(AsyncTestCase):
    def setUp(self):
        self.context = InjectionContext(enforce_typing=False)
        self.wallet = async_mock.create_autospec(BaseWallet)
        self.context.injector.bind_instance(BaseWallet, self.wallet)
        self.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.context,
        }
        self.test_did = "did"
        self.test_verkey = "verkey"

    async def test_missing_wallet(self):
        request = async_mock.MagicMock()
        request.app = self.app
        self.context.injector.clear_binding(BaseWallet)

        with self.assertRaises(HTTPForbidden):
            await test_module.wallet_create_did(request)

        with self.assertRaises(HTTPForbidden):
            await test_module.wallet_did_list(request)

        with self.assertRaises(HTTPForbidden):
            await test_module.wallet_get_public_did(request)

        with self.assertRaises(HTTPForbidden):
            await test_module.wallet_set_public_did(request)

    def test_format_did_info(self):
        did_info = DIDInfo(self.test_did, self.test_verkey, {})
        result = test_module.format_did_info(did_info)
        assert (
            result["did"] == self.test_did
            and result["verkey"] == self.test_verkey
            and result["public"] == "false"
        )
        did_info = DIDInfo(self.test_did, self.test_verkey, {"public": True})
        result = test_module.format_did_info(did_info)
        assert result["public"] == "true"

    async def test_create_did(self):
        request = async_mock.MagicMock()
        request.app = self.app
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response, async_mock.patch.object(
            test_module, "format_did_info", async_mock.Mock()
        ) as format_did_info:
            self.wallet.create_local_did.return_value = DIDInfo(
                self.test_did, self.test_verkey, {}
            )
            result = await test_module.wallet_create_did(request)
            format_did_info.assert_called_once_with(
                self.wallet.create_local_did.return_value
            )
            json_response.assert_called_once_with(
                {"result": format_did_info.return_value}
            )
            assert result is json_response.return_value

    async def test_did_list(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response, async_mock.patch.object(
            test_module, "format_did_info", async_mock.Mock()
        ) as format_did_info:
            self.wallet.get_local_dids.return_value = [
                DIDInfo(self.test_did, self.test_verkey, {})
            ]
            format_did_info.return_value = {"did": self.test_did}
            result = await test_module.wallet_did_list(request)
            format_did_info.assert_called_once_with(
                self.wallet.get_local_dids.return_value[0]
            )
            json_response.assert_called_once_with(
                {"results": [format_did_info.return_value]}
            )
            assert json_response.return_value is json_response()
            assert result is json_response.return_value

    async def test_get_public_did(self):
        request = async_mock.MagicMock()
        request.app = self.app
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response, async_mock.patch.object(
            test_module, "format_did_info", async_mock.Mock()
        ) as format_did_info:
            self.wallet.get_public_did.return_value = DIDInfo(
                self.test_did, self.test_verkey, {}
            )
            result = await test_module.wallet_get_public_did(request)
            format_did_info.assert_called_once_with(
                self.wallet.get_public_did.return_value
            )
            json_response.assert_called_once_with(
                {"result": format_did_info.return_value}
            )
            assert result is json_response.return_value

    async def test_set_public_did(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {"did": self.test_did}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response, async_mock.patch.object(
            test_module, "format_did_info", async_mock.Mock()
        ) as format_did_info:
            self.wallet.get_public_did.return_value = DIDInfo(
                self.test_did, self.test_verkey, {}
            )
            result = await test_module.wallet_set_public_did(request)
            self.wallet.set_public_did.assert_awaited_once_with(request.query["did"])
            format_did_info.assert_called_once_with(
                self.wallet.set_public_did.return_value
            )
            json_response.assert_called_once_with(
                {"result": format_did_info.return_value}
            )
            assert result is json_response.return_value
