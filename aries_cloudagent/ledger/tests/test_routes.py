from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
import pytest

from aiohttp.web import HTTPForbidden

from ...config.injection_context import InjectionContext
from ...ledger.base import BaseLedger

from .. import routes as test_module


class TestLedgerRoutes(AsyncTestCase):
    def setUp(self):
        self.context = InjectionContext(enforce_typing=False)
        self.ledger = async_mock.create_autospec(BaseLedger)
        self.context.injector.bind_instance(BaseLedger, self.ledger)
        self.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.context,
        }
        self.test_did = "did"
        self.test_verkey = "verkey"
        self.test_endpoint = "http://localhost:8021"

    async def test_missing_ledger(self):
        request = async_mock.MagicMock()
        request.app = self.app
        self.context.injector.clear_binding(BaseLedger)

        with self.assertRaises(HTTPForbidden):
            await test_module.register_ledger_nym(request)

        with self.assertRaises(HTTPForbidden):
            await test_module.get_did_verkey(request)

        with self.assertRaises(HTTPForbidden):
            await test_module.get_did_endpoint(request)


    async def test_get_verkey(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {"did": self.test_did}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            result = await test_module.get_did_verkey(request)
            self.ledger.get_key_for_did.return_value = self.test_verkey
            json_response.assert_called_once_with(
                {"verkey": self.test_verkey}
            )
            assert result is json_response.return_value

    async def test_get_endpoint(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {"did": self.test_did}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            result = await test_module.get_did_endpoint(request)
            self.ledger.get_endpoint_for_did.return_value = self.test_endpoint
            json_response.assert_called_once_with(
                {"endpoint": self.test_endpoint}
            )
            assert result is json_response.return_value


    async def test_register_nym(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {
            "did": self.test_did,
            "verkey": self.test_verkey
        }
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            result = await test_module.register_ledger_nym(request)
            self.ledger.register_nym.return_value = True
            json_response.assert_called_once_with(
                {"success": True}
            )
            assert result is json_response.return_value
