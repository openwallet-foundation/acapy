from typing import Tuple

from unittest import IsolatedAsyncioTestCase
import mock as async_mock

from ...core.in_memory import InMemoryProfile
from ...ledger.base import BaseLedger
from ...ledger.endpoint_type import EndpointType
from ...ledger.multiple_ledger.ledger_requests_executor import (
    IndyLedgerRequestsExecutor,
)
from ...ledger.multiple_ledger.base_manager import (
    BaseMultipleLedgerManager,
)
from ...multitenant.base import BaseMultitenantManager
from ...multitenant.manager import MultitenantManager

from .. import routes as test_module
from ..indy import Role
from ...connections.models.conn_record import ConnRecord


class TestLedgerRoutes(IsolatedAsyncioTestCase):
    def setUp(self):
        self.ledger = async_mock.create_autospec(BaseLedger)
        self.ledger.pool_name = "pool.0"
        self.profile = InMemoryProfile.test_profile()
        self.context = self.profile.context
        setattr(self.context, "profile", self.profile)
        self.profile.context.injector.bind_instance(BaseLedger, self.ledger)
        self.request_dict = {
            "context": self.context,
            "outbound_message_router": async_mock.AsyncMock(),
        }
        self.request = async_mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
        )

        self.test_did = "did"
        self.test_verkey = "verkey"
        self.test_endpoint = "http://localhost:8021"
        self.test_endpoint_type = EndpointType.PROFILE
        self.test_endpoint_type_profile = "http://company.com/profile"

    async def test_missing_ledger(self):
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.AsyncMock(
                    return_value=(None, None)
                )
            ),
        )
        self.profile.context.injector.clear_binding(BaseLedger)
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.register_ledger_nym(self.request)

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.get_nym_role(self.request)

        with self.assertRaises(test_module.web.HTTPForbidden):
            self.request.query["did"] = "test"
            await test_module.get_nym_role(self.request)

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.rotate_public_did_keypair(self.request)

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.get_did_verkey(self.request)

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.get_did_endpoint(self.request)

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.ledger_accept_taa(self.request)

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.ledger_get_taa(self.request)

    async def test_get_verkey_a(self):
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.AsyncMock(
                    return_value=(None, self.ledger)
                )
            ),
        )
        self.request.query = {"did": self.test_did}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.get_key_for_did.return_value = self.test_verkey
            result = await test_module.get_did_verkey(self.request)
            json_response.assert_called_once_with(
                {"verkey": self.ledger.get_key_for_did.return_value}
            )
            assert result is json_response.return_value

    async def test_get_verkey_b(self):
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.AsyncMock(
                    return_value=("test_ledger_id", self.ledger)
                )
            ),
        )
        self.request.query = {"did": self.test_did}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.get_key_for_did.return_value = self.test_verkey
            result = await test_module.get_did_verkey(self.request)
            json_response.assert_called_once_with(
                {
                    "ledger_id": "test_ledger_id",
                    "verkey": self.ledger.get_key_for_did.return_value,
                }
            )
            assert result is json_response.return_value

    async def test_get_verkey_multitenant(self):
        self.context.injector.bind_instance(
            BaseMultitenantManager,
            async_mock.MagicMock(MultitenantManager, autospec=True),
        )
        self.request.query = {"did": self.test_did}
        with async_mock.patch.object(
            IndyLedgerRequestsExecutor,
            "get_ledger_for_identifier",
            async_mock.AsyncMock(return_value=("test_ledger_id", self.ledger)),
        ), async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.get_key_for_did.return_value = self.test_verkey
            result = await test_module.get_did_verkey(self.request)
            json_response.assert_called_once_with(
                {
                    "ledger_id": "test_ledger_id",
                    "verkey": self.ledger.get_key_for_did.return_value,
                }
            )
            assert result is json_response.return_value

    async def test_get_verkey_no_did(self):
        self.request.query = {"no": "did"}
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.get_did_verkey(self.request)

    async def test_get_verkey_did_not_public(self):
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.AsyncMock(
                    return_value=("test_ledger_id", self.ledger)
                )
            ),
        )
        self.request.query = {"did": self.test_did}
        self.ledger.get_key_for_did.return_value = None
        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.get_did_verkey(self.request)

    async def test_get_verkey_x(self):
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.AsyncMock(
                    return_value=(None, self.ledger)
                )
            ),
        )
        self.request.query = {"did": self.test_did}
        self.ledger.get_key_for_did.side_effect = test_module.LedgerError()
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.get_did_verkey(self.request)

    async def test_get_endpoint(self):
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.AsyncMock(
                    return_value=(None, self.ledger)
                )
            ),
        )
        self.request.query = {"did": self.test_did}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.get_endpoint_for_did.return_value = self.test_endpoint
            result = await test_module.get_did_endpoint(self.request)
            json_response.assert_called_once_with(
                {"endpoint": self.ledger.get_endpoint_for_did.return_value}
            )
            assert result is json_response.return_value

    async def test_get_endpoint_multitenant(self):
        self.context.injector.bind_instance(
            BaseMultitenantManager,
            async_mock.MagicMock(MultitenantManager, autospec=True),
        )
        self.request.query = {"did": self.test_did}
        with async_mock.patch.object(
            IndyLedgerRequestsExecutor,
            "get_ledger_for_identifier",
            async_mock.AsyncMock(return_value=("test_ledger_id", self.ledger)),
        ), async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.get_endpoint_for_did.return_value = self.test_endpoint
            result = await test_module.get_did_endpoint(self.request)
            json_response.assert_called_once_with(
                {
                    "ledger_id": "test_ledger_id",
                    "endpoint": self.ledger.get_endpoint_for_did.return_value,
                }
            )
            assert result is json_response.return_value

    async def test_get_endpoint_of_type_profile(self):
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.AsyncMock(
                    return_value=("test_ledger_id", self.ledger)
                )
            ),
        )
        self.request.query = {
            "did": self.test_did,
            "endpoint_type": self.test_endpoint_type.w3c,
        }
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.get_endpoint_for_did.return_value = (
                self.test_endpoint_type_profile
            )
            result = await test_module.get_did_endpoint(self.request)
            json_response.assert_called_once_with(
                {
                    "ledger_id": "test_ledger_id",
                    "endpoint": self.ledger.get_endpoint_for_did.return_value,
                }
            )
            assert result is json_response.return_value

    async def test_get_endpoint_no_did(self):
        self.request.query = {"no": "did"}
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.get_did_endpoint(self.request)

    async def test_get_endpoint_x(self):
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.AsyncMock(
                    return_value=("test_ledger_id", self.ledger)
                )
            ),
        )
        self.request.query = {"did": self.test_did}
        self.ledger.get_endpoint_for_did.side_effect = test_module.LedgerError()
        with self.assertRaises(test_module.web.HTTPBadRequest):
            result = await test_module.get_did_endpoint(self.request)

    async def test_register_nym(self):
        self.request.query = {
            "did": self.test_did,
            "verkey": self.test_verkey,
            "role": "reset",
        }
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            success: bool = True
            txn: dict = None
            self.ledger.register_nym.return_value: Tuple[bool, dict] = (success, txn)
            result = await test_module.register_ledger_nym(self.request)
            json_response.assert_called_once_with({"success": success})
            assert result is json_response.return_value

    async def test_register_nym_bad_request(self):
        self.request.query = {"no": "did"}
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.register_ledger_nym(self.request)

    async def test_register_nym_ledger_txn_error(self):
        self.request.query = {"did": self.test_did, "verkey": self.test_verkey}
        self.ledger.register_nym.side_effect = test_module.LedgerTransactionError(
            "Error"
        )
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.register_ledger_nym(self.request)

    async def test_register_nym_ledger_error(self):
        self.request.query = {"did": self.test_did, "verkey": self.test_verkey}
        self.ledger.register_nym.side_effect = test_module.LedgerError("Error")
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.register_ledger_nym(self.request)

    async def test_register_nym_wallet_not_found_error(self):
        self.request.query = {"did": self.test_did, "verkey": self.test_verkey}
        self.ledger.register_nym.side_effect = test_module.WalletNotFoundError("Error")
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.register_ledger_nym(self.request)

    async def test_register_nym_wallet_error(self):
        self.request.query = {"did": self.test_did, "verkey": self.test_verkey}
        self.ledger.register_nym.side_effect = test_module.WalletError("Error")
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.register_ledger_nym(self.request)

    async def test_register_nym_create_transaction_for_endorser(self):
        self.request.query = {
            "did": "a_test_did",
            "verkey": "a_test_verkey",
            "alias": "did_alias",
            "role": "ENDORSER",
            "create_transaction_for_endorser": "true",
            "conn_id": "dummy",
        }

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.AsyncMock()
        ) as mock_conn_rec_retrieve, async_mock.patch.object(
            test_module, "TransactionManager", async_mock.MagicMock()
        ) as mock_txn_mgr, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_txn_mgr.return_value = async_mock.MagicMock(
                create_record=async_mock.AsyncMock(
                    return_value=async_mock.MagicMock(
                        serialize=async_mock.MagicMock(return_value={"...": "..."})
                    )
                )
            )
            mock_conn_rec_retrieve.return_value = async_mock.MagicMock(
                metadata_get=async_mock.AsyncMock(
                    return_value={
                        "endorser_did": ("did"),
                        "endorser_name": ("name"),
                    }
                )
            )
            self.ledger.register_nym.return_value: Tuple[bool, dict] = (
                True,
                {"signed_txn": {"...": "..."}},
            )

            result = await test_module.register_ledger_nym(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {"success": True, "txn": {"signed_txn": {"...": "..."}}}
            )

    async def test_register_nym_create_transaction_for_endorser_no_public_did(self):
        self.request.query = {
            "did": "a_test_did",
            "verkey": "a_test_verkey",
            "alias": "did_alias",
            "role": "reset",
            "create_transaction_for_endorser": "true",
            "conn_id": "dummy",
        }
        self.profile.context.settings["endorser.author"] = True

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.AsyncMock()
        ) as mock_conn_rec_retrieve, async_mock.patch.object(
            test_module, "TransactionManager", async_mock.MagicMock()
        ) as mock_txn_mgr, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_txn_mgr.return_value = async_mock.MagicMock(
                create_record=async_mock.AsyncMock(
                    return_value=async_mock.MagicMock(
                        serialize=async_mock.MagicMock(return_value={"...": "..."})
                    )
                )
            )
            mock_conn_rec_retrieve.return_value = async_mock.MagicMock(
                metadata_get=async_mock.AsyncMock(
                    return_value={
                        "endorser_did": ("did"),
                        "endorser_name": ("name"),
                    }
                )
            )
            self.ledger.register_nym.return_value: Tuple[bool, dict] = (
                True,
                {"signed_txn": {"...": "..."}},
            )

            result = await test_module.register_ledger_nym(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {"success": True, "txn": {"signed_txn": {"...": "..."}}}
            )

    async def test_register_nym_create_transaction_for_endorser_storage_x(self):
        self.request.query = {
            "did": "a_test_did",
            "verkey": "a_test_verkey",
            "alias": "did_alias",
            "role": "ENDORSER",
            "create_transaction_for_endorser": "true",
            "conn_id": "dummy",
        }

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.AsyncMock()
        ) as mock_conn_rec_retrieve, async_mock.patch.object(
            test_module, "TransactionManager", async_mock.MagicMock()
        ) as mock_txn_mgr:
            mock_txn_mgr.return_value = async_mock.MagicMock(
                create_record=async_mock.AsyncMock(
                    side_effect=test_module.StorageError()
                )
            )
            mock_conn_rec_retrieve.return_value = async_mock.MagicMock(
                metadata_get=async_mock.AsyncMock(
                    return_value={
                        "endorser_did": ("did"),
                        "endorser_name": ("name"),
                    }
                )
            )
            self.ledger.register_nym.return_value: Tuple[bool, dict] = (
                True,
                {"signed_txn": {"...": "..."}},
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.register_ledger_nym(self.request)

    async def test_register_nym_create_transaction_for_endorser_not_found_x(self):
        self.request.query = {
            "did": "a_test_did",
            "verkey": "a_test_verkey",
            "alias": "did_alias",
            "role": "ENDORSER",
            "create_transaction_for_endorser": "true",
            "conn_id": "dummy",
        }

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.AsyncMock()
        ) as mock_conn_rec_retrieve:
            mock_conn_rec_retrieve.side_effect = test_module.StorageNotFoundError()
            self.ledger.register_nym.return_value: Tuple[bool, dict] = (
                True,
                {"signed_txn": {"...": "..."}},
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.register_ledger_nym(self.request)

    async def test_register_nym_create_transaction_for_endorser_base_model_x(self):
        self.request.query = {
            "did": "a_test_did",
            "verkey": "a_test_verkey",
            "alias": "did_alias",
            "role": "ENDORSER",
            "create_transaction_for_endorser": "true",
            "conn_id": "dummy",
        }

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.AsyncMock()
        ) as mock_conn_rec_retrieve:
            mock_conn_rec_retrieve.side_effect = test_module.BaseModelError()
            self.ledger.register_nym.return_value: Tuple[bool, dict] = (
                True,
                {"signed_txn": {"...": "..."}},
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.register_ledger_nym(self.request)

    async def test_register_nym_create_transaction_for_endorser_no_endorser_info_x(
        self,
    ):
        self.request.query = {
            "did": "a_test_did",
            "verkey": "a_test_verkey",
            "alias": "did_alias",
            "role": "ENDORSER",
            "create_transaction_for_endorser": "true",
            "conn_id": "dummy",
        }

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.AsyncMock()
        ) as mock_conn_rec_retrieve:
            mock_conn_rec_retrieve.return_value = async_mock.MagicMock(
                metadata_get=async_mock.AsyncMock(return_value=None)
            )
            self.ledger.register_nym.return_value: Tuple[bool, dict] = (
                True,
                {"signed_txn": {"...": "..."}},
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.register_ledger_nym(self.request)

    async def test_register_nym_create_transaction_for_endorser_no_endorser_did_x(self):
        self.request.query = {
            "did": "a_test_did",
            "verkey": "a_test_verkey",
            "alias": "did_alias",
            "role": "ENDORSER",
            "create_transaction_for_endorser": "true",
            "conn_id": "dummy",
        }

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.AsyncMock()
        ) as mock_conn_rec_retrieve:
            mock_conn_rec_retrieve.return_value = async_mock.MagicMock(
                metadata_get=async_mock.AsyncMock(
                    return_value={
                        "endorser_name": ("name"),
                    }
                )
            )
            self.ledger.register_nym.return_value: Tuple[bool, dict] = (
                True,
                {"signed_txn": {"...": "..."}},
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.register_ledger_nym(self.request)

    async def test_get_nym_role_a(self):
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.AsyncMock(
                    return_value=(None, self.ledger)
                )
            ),
        )
        self.request.query = {"did": self.test_did}

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.get_nym_role.return_value = Role.USER
            result = await test_module.get_nym_role(self.request)
            json_response.assert_called_once_with({"role": "USER"})
            assert result is json_response.return_value

    async def test_get_nym_role_b(self):
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.AsyncMock(
                    return_value=("test_ledger_id", self.ledger)
                )
            ),
        )
        self.request.query = {"did": self.test_did}

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.get_nym_role.return_value = Role.USER
            result = await test_module.get_nym_role(self.request)
            json_response.assert_called_once_with(
                {"ledger_id": "test_ledger_id", "role": "USER"}
            )
            assert result is json_response.return_value

    async def test_get_nym_role_multitenant(self):
        self.context.injector.bind_instance(
            BaseMultitenantManager,
            async_mock.MagicMock(MultitenantManager, autospec=True),
        )
        self.request.query = {"did": self.test_did}

        with async_mock.patch.object(
            IndyLedgerRequestsExecutor,
            "get_ledger_for_identifier",
            async_mock.AsyncMock(return_value=("test_ledger_id", self.ledger)),
        ), async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.get_nym_role.return_value = Role.USER
            result = await test_module.get_nym_role(self.request)
            json_response.assert_called_once_with(
                {"ledger_id": "test_ledger_id", "role": "USER"}
            )
            assert result is json_response.return_value

    async def test_get_nym_role_bad_request(self):
        self.request.query = {"no": "did"}
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.get_nym_role(self.request)

    async def test_get_nym_role_ledger_txn_error(self):
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.AsyncMock(
                    return_value=("test_ledger_id", self.ledger)
                )
            ),
        )
        self.request.query = {"did": self.test_did}
        self.ledger.get_nym_role.side_effect = test_module.LedgerTransactionError(
            "Error in building get-nym request"
        )
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.get_nym_role(self.request)

    async def test_get_nym_role_bad_ledger_req(self):
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.AsyncMock(
                    return_value=("test_ledger_id", self.ledger)
                )
            ),
        )
        self.request.query = {"did": self.test_did}
        self.ledger.get_nym_role.side_effect = test_module.BadLedgerRequestError(
            "No such public DID"
        )
        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.get_nym_role(self.request)

    async def test_get_nym_role_ledger_error(self):
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.AsyncMock(
                    return_value=(None, self.ledger)
                )
            ),
        )
        self.request.query = {"did": self.test_did}
        self.ledger.get_nym_role.side_effect = test_module.LedgerError("Error")
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.get_nym_role(self.request)

    async def test_rotate_public_did_keypair(self):
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.rotate_public_did_keypair = async_mock.AsyncMock()

            await test_module.rotate_public_did_keypair(self.request)
            json_response.assert_called_once_with({})

    async def test_rotate_public_did_keypair_public_wallet_x(self):
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.rotate_public_did_keypair = async_mock.AsyncMock(
                side_effect=test_module.WalletError("Exception")
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.rotate_public_did_keypair(self.request)

    async def test_get_taa(self):
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.get_txn_author_agreement.return_value = {"taa_required": False}
            self.ledger.get_latest_txn_author_acceptance.return_value = None
            result = await test_module.ledger_get_taa(self.request)
            json_response.assert_called_once_with(
                {"result": {"taa_accepted": None, "taa_required": False}}
            )
            assert result is json_response.return_value

    async def test_get_taa_required(self):
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
            result = await test_module.ledger_get_taa(self.request)
            taa_info["taa_accepted"] = accepted
            json_response.assert_called_once_with({"result": taa_info})
            assert result is json_response.return_value

    async def test_get_taa_x(self):
        self.ledger.get_txn_author_agreement.side_effect = test_module.LedgerError()

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.ledger_get_taa(self.request)

    async def test_taa_accept_not_required(self):
        self.request.json = async_mock.AsyncMock(
            return_value={
                "version": "version",
                "text": "text",
                "mechanism": "mechanism",
            }
        )

        with self.assertRaises(test_module.web.HTTPBadRequest):
            self.ledger.get_txn_author_agreement.return_value = {"taa_required": False}
            await test_module.ledger_accept_taa(self.request)

    async def test_accept_taa(self):
        self.request.json = async_mock.AsyncMock(
            return_value={
                "version": "version",
                "text": "text",
                "mechanism": "mechanism",
            }
        )

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.ledger.get_txn_author_agreement.return_value = {
                "taa_record": {"text": "text"},
                "taa_required": True,
            }
            result = await test_module.ledger_accept_taa(self.request)
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
        self.request.json = async_mock.AsyncMock(
            return_value={
                "version": "version",
                "text": "text",
                "mechanism": "mechanism",
            }
        )
        self.ledger.get_txn_author_agreement.return_value = {
            "taa_record": {"text": "text"},
            "taa_required": True,
        }
        self.ledger.accept_txn_author_agreement.side_effect = test_module.StorageError()
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.ledger_accept_taa(self.request)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]

    async def test_get_write_ledger(self):
        self.profile.context.injector.bind_instance(
            BaseMultipleLedgerManager,
            async_mock.MagicMock(
                get_ledger_id_by_ledger_pool_name=async_mock.AsyncMock(
                    return_value="test_ledger_id"
                )
            ),
        )
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            result = await test_module.get_write_ledger(self.request)
            json_response.assert_called_once_with(
                {
                    "ledger_id": "test_ledger_id",
                }
            )
            assert result is json_response.return_value

    async def test_get_write_ledger_single_ledger(self):
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            result = await test_module.get_write_ledger(self.request)
            json_response.assert_called_once_with(
                {
                    "ledger_id": "default",
                }
            )
            assert result is json_response.return_value

    async def test_get_ledger_config(self):
        self.profile.context.injector.bind_instance(
            BaseMultipleLedgerManager,
            async_mock.MagicMock(
                get_prod_ledgers=async_mock.AsyncMock(
                    return_value={
                        "test_1": async_mock.MagicMock(),
                        "test_2": async_mock.MagicMock(),
                        "test_5": async_mock.MagicMock(),
                    }
                ),
                get_nonprod_ledgers=async_mock.AsyncMock(
                    return_value={
                        "test_3": async_mock.MagicMock(),
                        "test_4": async_mock.MagicMock(),
                    }
                ),
            ),
        )
        self.context.settings["ledger.ledger_config_list"] = [
            {"id": "test_1", "genesis_transactions": "..."},
            {"id": "test_2", "genesis_transactions": "..."},
            {"id": "test_3", "genesis_transactions": "..."},
            {"id": "test_4", "genesis_transactions": "..."},
        ]
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            result = await test_module.get_ledger_config(self.request)
            json_response.assert_called_once_with(
                {
                    "production_ledgers": [
                        {"id": "test_1"},
                        {"id": "test_2"},
                        {
                            "id": "test_5",
                            "desc": "ledger configured outside --genesis-transactions-list",
                        },
                    ],
                    "non_production_ledgers": [{"id": "test_3"}, {"id": "test_4"}],
                }
            )
            assert result is json_response.return_value

    async def test_get_ledger_config_x(self):
        with self.assertRaises(test_module.web.HTTPForbidden) as cm:
            await test_module.get_ledger_config(self.request)
            assert "No instance provided for BaseMultipleLedgerManager" in cm
