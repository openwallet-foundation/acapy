from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ....admin.request_context import AdminRequestContext
from ....core.in_memory import InMemoryProfile
from ....indy.issuer import IndyIssuer
from ....ledger.base import BaseLedger
from ....ledger.multiple_ledger.ledger_requests_executor import (
    IndyLedgerRequestsExecutor,
)
from ....multitenant.base import BaseMultitenantManager
from ....multitenant.manager import MultitenantManager
from ....storage.base import BaseStorage

from .. import routes as test_module
from ....connections.models.conn_record import ConnRecord


SCHEMA_ID = "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0"


class TestSchemaRoutes(AsyncTestCase):
    def setUp(self):
        self.session_inject = {}
        self.profile = InMemoryProfile.test_profile()
        self.profile_injector = self.profile.context.injector
        self.ledger = async_mock.create_autospec(BaseLedger)
        self.ledger.__aenter__ = async_mock.CoroutineMock(return_value=self.ledger)
        self.ledger.create_and_send_schema = async_mock.CoroutineMock(
            return_value=(SCHEMA_ID, {"schema": "def", "signed_txn": "..."})
        )
        self.ledger.get_schema = async_mock.CoroutineMock(
            return_value={"schema": "def", "signed_txn": "..."}
        )
        self.profile_injector.bind_instance(BaseLedger, self.ledger)

        self.issuer = async_mock.create_autospec(IndyIssuer)
        self.profile_injector.bind_instance(IndyIssuer, self.issuer)

        self.storage = async_mock.create_autospec(BaseStorage)
        self.storage.find_all_records = async_mock.CoroutineMock(
            return_value=[async_mock.MagicMock(value=SCHEMA_ID)]
        )
        self.session_inject[BaseStorage] = self.storage
        self.context = AdminRequestContext.test_context(
            self.session_inject, profile=self.profile
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

    async def test_send_schema(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "schema_name": "schema_name",
                "schema_version": "1.0",
                "attributes": ["table", "drink", "colour"],
            }
        )

        self.request.query = {"create_transaction_for_endorser": "false"}

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.schemas_send_schema(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {
                    "sent": {
                        "schema_id": SCHEMA_ID,
                        "schema": {
                            "schema": "def",
                            "signed_txn": "...",
                        },
                    },
                    "schema_id": SCHEMA_ID,
                    "schema": {
                        "schema": "def",
                        "signed_txn": "...",
                    },
                }
            )

    async def test_send_schema_create_transaction_for_endorser(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "schema_name": "schema_name",
                "schema_version": "1.0",
                "attributes": ["table", "drink", "colour"],
            }
        )

        self.request.query = {
            "create_transaction_for_endorser": "true",
            "conn_id": "dummy",
        }

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve, async_mock.patch.object(
            test_module, "TransactionManager", async_mock.MagicMock()
        ) as mock_txn_mgr, async_mock.patch.object(
            test_module.web, "json_response", async_mock.MagicMock()
        ) as mock_response:
            mock_txn_mgr.return_value = async_mock.MagicMock(
                create_record=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        serialize=async_mock.MagicMock(return_value={"...": "..."})
                    )
                )
            )
            mock_conn_rec_retrieve.return_value = async_mock.MagicMock(
                metadata_get=async_mock.CoroutineMock(
                    return_value={
                        "endorser_did": ("did"),
                        "endorser_name": ("name"),
                    }
                )
            )
            result = await test_module.schemas_send_schema(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {
                    "sent": {
                        "schema_id": SCHEMA_ID,
                        "schema": {
                            "schema": "def",
                            "signed_txn": "...",
                        },
                    },
                    "txn": {"...": "..."},
                }
            )

    async def test_send_schema_create_transaction_for_endorser_storage_x(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "schema_name": "schema_name",
                "schema_version": "1.0",
                "attributes": ["table", "drink", "colour"],
            }
        )

        self.request.query = {
            "create_transaction_for_endorser": "true",
            "conn_id": "dummy",
        }

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve, async_mock.patch.object(
            test_module, "TransactionManager", async_mock.MagicMock()
        ) as mock_txn_mgr:
            mock_txn_mgr.return_value = async_mock.MagicMock(
                create_record=async_mock.CoroutineMock(
                    side_effect=test_module.StorageError()
                )
            )
            mock_conn_rec_retrieve.return_value = async_mock.MagicMock(
                metadata_get=async_mock.CoroutineMock(
                    return_value={
                        "endorser_did": ("did"),
                        "endorser_name": ("name"),
                    }
                )
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.schemas_send_schema(self.request)

    async def test_send_schema_create_transaction_for_endorser_not_found_x(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "schema_name": "schema_name",
                "schema_version": "1.0",
                "attributes": ["table", "drink", "colour"],
            }
        )

        self.request.query = {
            "create_transaction_for_endorser": "true",
            "conn_id": "dummy",
        }

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve:
            mock_conn_rec_retrieve.side_effect = test_module.StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.schemas_send_schema(self.request)

    async def test_send_schema_create_transaction_for_endorser_base_model_x(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "schema_name": "schema_name",
                "schema_version": "1.0",
                "attributes": ["table", "drink", "colour"],
            }
        )

        self.request.query = {
            "create_transaction_for_endorser": "true",
            "conn_id": "dummy",
        }

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve:
            mock_conn_rec_retrieve.side_effect = test_module.BaseModelError()

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.schemas_send_schema(self.request)

    async def test_send_schema_create_transaction_for_endorser_no_endorser_info_x(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "schema_name": "schema_name",
                "schema_version": "1.0",
                "attributes": ["table", "drink", "colour"],
            }
        )

        self.request.query = {
            "create_transaction_for_endorser": "true",
            "conn_id": "dummy",
        }

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve:
            mock_conn_rec_retrieve.return_value = async_mock.MagicMock(
                metadata_get=async_mock.CoroutineMock(return_value=None)
            )
            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.schemas_send_schema(self.request)

    async def test_send_schema_create_transaction_for_endorser_no_endorser_did_x(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "schema_name": "schema_name",
                "schema_version": "1.0",
                "attributes": ["table", "drink", "colour"],
            }
        )

        self.request.query = {
            "create_transaction_for_endorser": "true",
            "conn_id": "dummy",
        }

        with async_mock.patch.object(
            ConnRecord, "retrieve_by_id", async_mock.CoroutineMock()
        ) as mock_conn_rec_retrieve:
            mock_conn_rec_retrieve.return_value = async_mock.MagicMock(
                metadata_get=async_mock.CoroutineMock(
                    return_value={
                        "endorser_name": ("name"),
                    }
                )
            )
            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.schemas_send_schema(self.request)

    async def test_send_schema_no_ledger(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "schema_name": "schema_name",
                "schema_version": "1.0",
                "attributes": ["table", "drink", "colour"],
            }
        )

        self.context.injector.clear_binding(BaseLedger)
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.schemas_send_schema(self.request)

    async def test_send_schema_x_ledger(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "schema_name": "schema_name",
                "schema_version": "1.0",
                "attributes": ["table", "drink", "colour"],
            }
        )
        self.request.query = {"create_transaction_for_endorser": "false"}
        self.ledger.create_and_send_schema = async_mock.CoroutineMock(
            side_effect=test_module.LedgerError("Down for routine maintenance")
        )

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.schemas_send_schema(self.request)

    async def test_created(self):
        self.request.match_info = {"schema_id": SCHEMA_ID}

        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.schemas_created(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with({"schema_ids": [SCHEMA_ID]})

    async def test_get_schema(self):
        self.profile_injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.CoroutineMock(
                    return_value=("test_ledger_id", self.ledger)
                )
            ),
        )
        self.request.match_info = {"schema_id": SCHEMA_ID}
        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.schemas_get_schema(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {
                    "ledger_id": "test_ledger_id",
                    "schema": {"schema": "def", "signed_txn": "..."},
                }
            )

    async def test_get_schema_multitenant(self):
        self.profile_injector.bind_instance(
            BaseMultitenantManager,
            async_mock.MagicMock(MultitenantManager, autospec=True),
        )
        self.request.match_info = {"schema_id": SCHEMA_ID}
        with async_mock.patch.object(
            IndyLedgerRequestsExecutor,
            "get_ledger_for_identifier",
            async_mock.CoroutineMock(return_value=("test_ledger_id", self.ledger)),
        ), async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.schemas_get_schema(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {
                    "ledger_id": "test_ledger_id",
                    "schema": {"schema": "def", "signed_txn": "..."},
                }
            )

    async def test_get_schema_on_seq_no(self):
        self.profile_injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.CoroutineMock(
                    return_value=(None, self.ledger)
                )
            ),
        )
        self.request.match_info = {"schema_id": "12345"}
        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.schemas_get_schema(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {"schema": {"schema": "def", "signed_txn": "..."}}
            )

    async def test_get_schema_no_ledger(self):
        self.profile_injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.CoroutineMock(
                    return_value=(None, None)
                )
            ),
        )
        self.request.match_info = {"schema_id": SCHEMA_ID}
        self.ledger.get_schema = async_mock.CoroutineMock(
            side_effect=test_module.LedgerError("Down for routine maintenance")
        )

        self.context.injector.clear_binding(BaseLedger)
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.schemas_get_schema(self.request)

    async def test_get_schema_x_ledger(self):
        self.profile_injector.bind_instance(
            IndyLedgerRequestsExecutor,
            async_mock.MagicMock(
                get_ledger_for_identifier=async_mock.CoroutineMock(
                    return_value=(None, self.ledger)
                )
            ),
        )
        self.request.match_info = {"schema_id": SCHEMA_ID}
        self.ledger.get_schema = async_mock.CoroutineMock(
            side_effect=test_module.LedgerError("Down for routine maintenance")
        )

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.schemas_get_schema(self.request)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
