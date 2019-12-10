from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
import pytest

from aiohttp.web import HTTPBadRequest, HTTPForbidden

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
            self.ledger.get_key_for_did.return_value = self.test_verkey
            result = await test_module.get_did_verkey(request)
            json_response.assert_called_once_with(
                {"verkey": self.ledger.get_key_for_did.return_value}
            )
            assert result is json_response.return_value

    async def test_get_endpoint(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {"did": self.test_did}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.get_endpoint_for_did.return_value = self.test_endpoint
            result = await test_module.get_did_endpoint(request)
            json_response.assert_called_once_with(
                {"endpoint": self.ledger.get_endpoint_for_did.return_value}
            )
            assert result is json_response.return_value

    async def test_register_nym(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {"did": self.test_did, "verkey": self.test_verkey}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.register_nym.return_value = True
            result = await test_module.register_ledger_nym(request)
            json_response.assert_called_once_with(
                {"success": self.ledger.register_nym.return_value}
            )
            assert result is json_response.return_value

    async def test_taa_forbidden(self):
        request = async_mock.MagicMock()
        request.app = self.app

        with self.assertRaises(HTTPForbidden):
            await test_module.ledger_get_taa(request)

    async def test_get_taa(self):
        request = async_mock.MagicMock()
        request.app = self.app
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.LEDGER_TYPE = "indy"
            self.ledger.get_txn_author_agreement.return_value = {"taa_required": False}
            self.ledger.get_latest_txn_author_acceptance.return_value = None
            result = await test_module.ledger_get_taa(request)
            json_response.assert_called_once_with(
                {"result": {"taa_accepted": None, "taa_required": False}}
            )
            assert result is json_response.return_value

    async def test_taa_accept_not_required(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.json = async_mock.CoroutineMock(
            return_value={
                "version": "version",
                "text": "text",
                "mechanism": "mechanism",
            }
        )

        with self.assertRaises(HTTPBadRequest):
            self.ledger.LEDGER_TYPE = "indy"
            self.ledger.get_txn_author_agreement.return_value = {"taa_required": False}
            await test_module.ledger_accept_taa(request)

    async def test_accept_taa(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.json = async_mock.CoroutineMock(
            return_value={
                "version": "version",
                "text": "text",
                "mechanism": "mechanism",
            }
        )

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.LEDGER_TYPE = "indy"
            self.ledger.get_txn_author_agreement.return_value = {"taa_required": True}
            result = await test_module.ledger_accept_taa(request)
            json_response.assert_called_once_with({})
            self.ledger.accept_txn_author_agreement.assert_awaited_once_with(
                {
                    "version": "version",
                    "text": "text",
                    "digest": self.ledger.taa_digest.return_value,
                },
                "mechanism",
            )
            assert result is json_response.return_value
