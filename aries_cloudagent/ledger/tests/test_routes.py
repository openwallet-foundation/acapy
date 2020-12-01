from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
import pytest

from ...config.injection_context import InjectionContext
from ...config.injector import Injector
from ...ledger.base import BaseLedger
from ...ledger.endpoint_type import EndpointType
from ...messaging.request_context import RequestContext

from .. import routes as test_module
from ..indy import Role


class TestLedgerRoutes(AsyncTestCase):
    def setUp(self):
        self.injector = Injector(enforce_typing=False)

        def _inject(cls, required: bool = True):
            return self.injector.inject(cls, required=required)

        self.ledger = async_mock.create_autospec(BaseLedger)
        self.ledger.pool_name = "pool.0"
        self.injector.bind_instance(BaseLedger, self.ledger)

        self.session = async_mock.MagicMock(inject=_inject)
        self.context = RequestContext.test_context()
        setattr(
            self.context, "session", async_mock.CoroutineMock(return_value=self.session)
        )

        self.app = {
            "outbound_message_router": async_mock.CoroutineMock(),
            "request_context": self.context,
        }
        self.test_did = "did"
        self.test_verkey = "verkey"
        self.test_endpoint = "http://localhost:8021"
        self.test_endpoint_type = EndpointType.PROFILE
        self.test_endpoint_type_profile = "http://company.com/profile"

    async def test_missing_ledger(self):
        request = async_mock.MagicMock(
            app=self.app,
        )
        self.injector.clear_binding(BaseLedger)

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.register_ledger_nym(request)

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.get_nym_role(request)

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.rotate_public_did_keypair(request)

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.get_did_verkey(request)

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.get_did_endpoint(request)

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.ledger_accept_taa(request)

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

    async def test_get_verkey_no_did(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {"no": "did"}
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.get_did_verkey(request)

    async def test_get_verkey_did_not_public(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {"did": self.test_did}
        self.ledger.get_key_for_did.return_value = None
        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.get_did_verkey(request)

    async def test_get_verkey_x(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {"did": self.test_did}
        self.ledger.get_key_for_did.side_effect = test_module.LedgerError()
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.get_did_verkey(request)

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

    async def test_get_endpoint_of_type_profile(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {
            "did": self.test_did,
            "endpoint_type": self.test_endpoint_type.w3c,
        }
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.get_endpoint_for_did.return_value = (
                self.test_endpoint_type_profile
            )
            result = await test_module.get_did_endpoint(request)
            json_response.assert_called_once_with(
                {"endpoint": self.ledger.get_endpoint_for_did.return_value}
            )
            assert result is json_response.return_value

    async def test_get_endpoint_no_did(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {"no": "did"}
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.get_did_endpoint(request)

    async def test_get_endpoint_x(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {"did": self.test_did}
        self.ledger.get_endpoint_for_did.side_effect = test_module.LedgerError()
        with self.assertRaises(test_module.web.HTTPBadRequest):
            result = await test_module.get_did_endpoint(request)

    async def test_register_nym(self):
        request = async_mock.MagicMock(
            app=self.app,
            query={
                "did": self.test_did,
                "verkey": self.test_verkey,
                "role": "reset",
            },
        )
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.register_nym.return_value = True
            result = await test_module.register_ledger_nym(request)
            json_response.assert_called_once_with(
                {"success": self.ledger.register_nym.return_value}
            )
            assert result is json_response.return_value

    async def test_register_nym_bad_request(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {"no": "did"}
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.register_ledger_nym(request)

    async def test_register_nym_ledger_txn_error(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {"did": self.test_did, "verkey": self.test_verkey}
        self.ledger.register_nym.side_effect = test_module.LedgerTransactionError(
            "Error"
        )
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.register_ledger_nym(request)

    async def test_register_nym_ledger_error(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {"did": self.test_did, "verkey": self.test_verkey}
        self.ledger.register_nym.side_effect = test_module.LedgerError("Error")
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.register_ledger_nym(request)

    async def test_register_nym_wallet_error(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {"did": self.test_did, "verkey": self.test_verkey}
        self.ledger.register_nym.side_effect = test_module.WalletError("Error")
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.register_ledger_nym(request)

    async def test_get_nym_role(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {"did": self.test_did}

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.get_nym_role.return_value = Role.USER
            result = await test_module.get_nym_role(request)
            json_response.assert_called_once_with({"role": "USER"})
            assert result is json_response.return_value

    async def test_get_nym_role_bad_request(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {"no": "did"}
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.get_nym_role(request)

    async def test_get_nym_role_ledger_txn_error(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {"did": self.test_did}
        self.ledger.get_nym_role.side_effect = test_module.LedgerTransactionError(
            "Error in building get-nym request"
        )
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.get_nym_role(request)

    async def test_get_nym_role_bad_ledger_req(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {"did": self.test_did}
        self.ledger.get_nym_role.side_effect = test_module.BadLedgerRequestError(
            "No such public DID"
        )
        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.get_nym_role(request)

    async def test_get_nym_role_ledger_error(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.query = {"did": self.test_did}
        self.ledger.get_nym_role.side_effect = test_module.LedgerError("Error")
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.get_nym_role(request)

    async def test_rotate_public_did_keypair(self):
        request = async_mock.MagicMock()
        request.app = self.app

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.rotate_public_did_keypair = async_mock.CoroutineMock()

            await test_module.rotate_public_did_keypair(request)
            json_response.assert_called_once_with({})

    async def test_rotate_public_did_keypair_public_wallet_x(self):
        request = async_mock.MagicMock()
        request.app = self.app

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.rotate_public_did_keypair = async_mock.CoroutineMock(
                side_effect=test_module.WalletError("Exception")
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.rotate_public_did_keypair(request)

    async def test_get_taa(self):
        request = async_mock.MagicMock()
        request.app = self.app
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.get_txn_author_agreement.return_value = {"taa_required": False}
            self.ledger.get_latest_txn_author_acceptance.return_value = None
            result = await test_module.ledger_get_taa(request)
            json_response.assert_called_once_with(
                {"result": {"taa_accepted": None, "taa_required": False}}
            )
            assert result is json_response.return_value

    async def test_get_taa_required(self):
        request = async_mock.MagicMock()
        request.app = self.app
        accepted = {
            "mechanism": "dummy",
            "time": 1234567890,
        }
        taa_info = {"taa_required": True}

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.get_txn_author_agreement.return_value = taa_info
            self.ledger.get_latest_txn_author_acceptance.return_value = accepted
            result = await test_module.ledger_get_taa(request)
            taa_info["taa_accepted"] = accepted
            json_response.assert_called_once_with({"result": taa_info})
            assert result is json_response.return_value

    async def test_get_taa_x(self):
        request = async_mock.MagicMock()
        request.app = self.app

        self.ledger.get_txn_author_agreement.side_effect = test_module.LedgerError()

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.ledger_get_taa(request)

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

        with self.assertRaises(test_module.web.HTTPBadRequest):
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

    async def test_accept_taa_x(self):
        request = async_mock.MagicMock()
        request.app = self.app
        request.json = async_mock.CoroutineMock(
            return_value={
                "version": "version",
                "text": "text",
                "mechanism": "mechanism",
            }
        )
        self.ledger.get_txn_author_agreement.return_value = {"taa_required": True}
        self.ledger.accept_txn_author_agreement.side_effect = test_module.StorageError()
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.ledger_accept_taa(request)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
