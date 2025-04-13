from unittest import IsolatedAsyncioTestCase

from ....admin.request_context import AdminRequestContext
from ....connections.models.conn_record import ConnRecord
from ....indy.issuer import IndyIssuer
from ....ledger.base import BaseLedger
from ....ledger.multiple_ledger.ledger_requests_executor import IndyLedgerRequestsExecutor
from ....multitenant.base import BaseMultitenantManager
from ....multitenant.manager import MultitenantManager
from ....storage.base import BaseStorage
from ....tests import mock
from ....utils.testing import create_test_profile
from .. import routes as test_module

SCHEMA_ID = "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0"
CRED_DEF_ID = "WgWxqztrNooG92RXvxSTWv:3:CL:20:tag"


class TestCredentialDefinitionRoutes(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.session_inject = {}
        self.profile = await create_test_profile(
            settings={
                "admin.admin_api_key": "secret-key",
            }
        )
        self.profile_injector = self.profile.context.injector

        self.ledger = mock.create_autospec(BaseLedger)
        self.ledger.__aenter__ = mock.CoroutineMock(return_value=self.ledger)
        self.ledger.create_and_send_credential_definition = mock.CoroutineMock(
            return_value=(
                CRED_DEF_ID,
                {"cred": "def", "signed_txn": "..."},
                True,
            )
        )
        self.ledger.get_credential_definition = mock.CoroutineMock(
            return_value={"cred": "def", "signed_txn": "..."}
        )
        self.profile_injector.bind_instance(BaseLedger, self.ledger)

        self.issuer = mock.create_autospec(IndyIssuer)
        self.profile_injector.bind_instance(IndyIssuer, self.issuer)

        self.storage = mock.create_autospec(BaseStorage)
        self.storage.find_all_records = mock.CoroutineMock(
            return_value=[mock.MagicMock(value=CRED_DEF_ID)]
        )
        self.session_inject[BaseStorage] = self.storage

        self.context = AdminRequestContext.test_context(
            self.session_inject, profile=self.profile
        )
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

    async def test_send_credential_definition(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "schema_id": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
                "support_revocation": False,
                "tag": "tag",
            }
        )

        self.request.query = {"create_transaction_for_endorser": "false"}

        with mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.credential_definitions_send_credential_definition(
                self.request
            )
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {
                    "sent": {"credential_definition_id": CRED_DEF_ID},
                    "credential_definition_id": CRED_DEF_ID,
                }
            )

    async def test_send_credential_definition_create_transaction_for_endorser(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "schema_id": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
                "support_revocation": False,
                "tag": "tag",
            }
        )

        self.request.query = {
            "create_transaction_for_endorser": "true",
            "conn_id": "dummy",
        }

        with (
            mock.patch.object(
                ConnRecord, "retrieve_by_id", mock.CoroutineMock()
            ) as mock_conn_rec_retrieve,
            mock.patch.object(
                test_module, "TransactionManager", mock.MagicMock()
            ) as mock_txn_mgr,
            mock.patch.object(
                test_module.web, "json_response", mock.MagicMock()
            ) as mock_response,
        ):
            mock_txn_mgr.return_value = mock.MagicMock(
                create_record=mock.CoroutineMock(
                    return_value=mock.MagicMock(
                        serialize=mock.MagicMock(return_value={"...": "..."})
                    )
                )
            )
            mock_conn_rec_retrieve.return_value = mock.MagicMock(
                metadata_get=mock.CoroutineMock(
                    return_value={
                        "endorser_did": ("did"),
                        "endorser_name": ("name"),
                    }
                )
            )
            result = await test_module.credential_definitions_send_credential_definition(
                self.request
            )
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {
                    "sent": {"credential_definition_id": CRED_DEF_ID},
                    "txn": {"...": "..."},
                }
            )

    async def test_send_credential_definition_create_transaction_for_endorser_storage_x(
        self,
    ):
        self.request.json = mock.CoroutineMock(
            return_value={
                "schema_id": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
                "support_revocation": False,
                "tag": "tag",
            }
        )

        self.request.query = {
            "create_transaction_for_endorser": "true",
            "conn_id": "dummy",
        }

        with (
            mock.patch.object(
                ConnRecord, "retrieve_by_id", mock.CoroutineMock()
            ) as mock_conn_rec_retrieve,
            mock.patch.object(
                test_module, "TransactionManager", mock.MagicMock()
            ) as mock_txn_mgr,
        ):
            mock_conn_rec_retrieve.return_value = mock.MagicMock(
                metadata_get=mock.CoroutineMock(
                    return_value={
                        "endorser_did": ("did"),
                        "endorser_name": ("name"),
                    }
                )
            )
            mock_txn_mgr.return_value = mock.MagicMock(
                create_record=mock.CoroutineMock(side_effect=test_module.StorageError())
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_definitions_send_credential_definition(
                    self.request
                )

    async def test_send_credential_definition_create_transaction_for_endorser_not_found_x(
        self,
    ):
        self.request.json = mock.CoroutineMock(
            return_value={
                "schema_id": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
                "support_revocation": False,
                "tag": "tag",
            }
        )

        self.request.query = {
            "create_transaction_for_endorser": "true",
            "conn_id": "dummy",
        }

        with mock.patch.object(
            ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve:
            mock_conn_rec_retrieve.side_effect = test_module.StorageNotFoundError()

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.credential_definitions_send_credential_definition(
                    self.request
                )

    async def test_send_credential_definition_create_transaction_for_endorser_base_model_x(
        self,
    ):
        self.request.json = mock.CoroutineMock(
            return_value={
                "schema_id": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
                "support_revocation": False,
                "tag": "tag",
            }
        )

        self.request.query = {
            "create_transaction_for_endorser": "true",
            "conn_id": "dummy",
        }

        with mock.patch.object(
            ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve:
            mock_conn_rec_retrieve.side_effect = test_module.BaseModelError()

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_definitions_send_credential_definition(
                    self.request
                )

    async def test_send_credential_definition_create_transaction_for_endorser_no_endorser_info_x(
        self,
    ):
        self.request.json = mock.CoroutineMock(
            return_value={
                "schema_id": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
                "support_revocation": False,
                "tag": "tag",
            }
        )

        self.request.query = {
            "create_transaction_for_endorser": "true",
            "conn_id": "dummy",
        }

        with mock.patch.object(
            ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve:
            mock_conn_rec_retrieve.return_value = mock.MagicMock(
                metadata_get=mock.CoroutineMock(return_value=None)
            )
            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_definitions_send_credential_definition(
                    self.request
                )

    async def test_send_credential_definition_create_transaction_for_endorser_no_endorser_did_x(
        self,
    ):
        self.request.json = mock.CoroutineMock(
            return_value={
                "schema_id": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
                "support_revocation": False,
                "tag": "tag",
            }
        )

        self.request.query = {
            "create_transaction_for_endorser": "true",
            "conn_id": "dummy",
        }

        with mock.patch.object(
            ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve:
            mock_conn_rec_retrieve.return_value = mock.MagicMock(
                metadata_get=mock.CoroutineMock(
                    return_value={
                        "endorser_name": ("name"),
                    }
                )
            )
            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.credential_definitions_send_credential_definition(
                    self.request
                )

    async def test_send_credential_definition_no_ledger(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "schema_id": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
                "support_revocation": False,
                "tag": "tag",
            }
        )

        self.context.injector.clear_binding(BaseLedger)
        self.profile_injector.clear_binding(BaseLedger)
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.credential_definitions_send_credential_definition(
                self.request
            )

    async def test_send_credential_definition_ledger_x(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "schema_id": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
                "support_revocation": False,
                "tag": "tag",
            }
        )

        self.request.query = {"create_transaction_for_endorser": "false"}

        self.ledger.__aenter__ = mock.CoroutineMock(
            side_effect=test_module.LedgerError("oops")
        )
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.credential_definitions_send_credential_definition(
                self.request
            )

    async def test_created(self):
        self.request.match_info = {"cred_def_id": CRED_DEF_ID}

        with mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.credential_definitions_created(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {"credential_definition_ids": [CRED_DEF_ID]}
            )

    async def test_get_credential_definition(self):
        mock_ledger_executor = mock.MagicMock(IndyLedgerRequestsExecutor, autospec=True)
        mock_ledger_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=("test_ledger_id", self.ledger)
        )
        self.profile_injector.bind_instance(
            IndyLedgerRequestsExecutor, mock_ledger_executor
        )
        self.request.match_info = {"cred_def_id": CRED_DEF_ID}
        with mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.credential_definitions_get_credential_definition(
                self.request
            )
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {
                    "ledger_id": "test_ledger_id",
                    "credential_definition": {"cred": "def", "signed_txn": "..."},
                }
            )

    async def test_get_credential_definition_multitenant(self):
        self.profile_injector.bind_instance(
            BaseMultitenantManager,
            mock.MagicMock(MultitenantManager, autospec=True),
        )
        self.request.match_info = {"cred_def_id": CRED_DEF_ID}
        with (
            mock.patch.object(
                IndyLedgerRequestsExecutor,
                "get_ledger_for_identifier",
                mock.CoroutineMock(return_value=("test_ledger_id", self.ledger)),
            ),
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            result = await test_module.credential_definitions_get_credential_definition(
                self.request
            )
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {
                    "ledger_id": "test_ledger_id",
                    "credential_definition": {"cred": "def", "signed_txn": "..."},
                }
            )

    async def test_get_credential_definition_no_ledger(self):
        mock_ledger_executor = mock.MagicMock(IndyLedgerRequestsExecutor, autospec=True)
        mock_ledger_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=(None, None)
        )
        self.profile_injector.bind_instance(
            IndyLedgerRequestsExecutor, mock_ledger_executor
        )

        self.request.match_info = {"cred_def_id": CRED_DEF_ID}
        self.context.injector.clear_binding(BaseLedger)
        self.profile_injector.clear_binding(BaseLedger)
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.credential_definitions_get_credential_definition(
                self.request
            )

    async def test_register(self):
        mock_app = mock.MagicMock()
        mock_app.add_routes = mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
