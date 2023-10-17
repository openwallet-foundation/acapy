from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
import pytest
from ....anoncreds.base import (
    AnonCredsResolutionError,
)
from ....anoncreds.default.legacy_indy.registry import LegacyIndyRegistry
from ....anoncreds.issuer import AnonCredsIssuer, AnonCredsIssuerError
from ....anoncreds.models.anoncreds_schema import (
    AnonCredsSchema,
    GetSchemaResult,
    SchemaResult,
    SchemaState,
)
from ....anoncreds.registry import AnonCredsRegistry
from ....askar.profile import AskarProfile
from ....wallet.crypto import ed25519_pk_to_curve25519

from ....wallet.did_info import DIDInfo
from ....wallet.did_method import SOV
from ....wallet.in_memory import InMemoryWallet

from ....admin.request_context import AdminRequestContext
from ....core.in_memory import InMemoryProfile
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
        self.profile = InMemoryProfile.test_profile(profile_class=AskarProfile)
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

        self.issuer = AnonCredsIssuer(self.profile)
        self.profile_injector.bind_instance(AnonCredsIssuer, self.issuer)

        self.indy_ledger = LegacyIndyRegistry()
        self.indy_ledger.get_schema = async_mock.CoroutineMock(
            return_value=GetSchemaResult(
                schema=AnonCredsSchema(
                    issuer_id="",
                    attr_names=["table", "drink", "colour"],
                    name="schema_name",
                    version="1.0",
                ),
                schema_id=SCHEMA_ID,
                resolution_metadata={"ledger_id": "test_ledger_id"},
                schema_metadata={"seqNo": "1"},
            )
        )

        self.registry = AnonCredsRegistry([self.indy_ledger])
        self.registry._registrar_for_identifier = async_mock.CoroutineMock(
            return_value=self.indy_ledger
        )

        self.indy_ledger_req_exec = IndyLedgerRequestsExecutor(self.profile)
        self.indy_ledger_req_exec.get_ledger_for_identifier = async_mock.CoroutineMock(
            return_value=("test_ledger_id", self.ledger)
        )

        self.profile_injector.bind_instance(LegacyIndyRegistry, self.indy_ledger)
        self.profile_injector.bind_instance(AnonCredsRegistry, self.registry)
        self.profile_injector.bind_instance(
            IndyLedgerRequestsExecutor, self.indy_ledger_req_exec
        )

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
        self.test_did = "55GkHamhTU1ZbTbV2ab9DE"
        self.test_did_info = DIDInfo(
            did=self.test_did,
            verkey="3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
            metadata={"test": "test"},
            method=SOV,
            key_type=ed25519_pk_to_curve25519,
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

        with async_mock.patch.object(
            InMemoryWallet,
            "get_public_did",
        ) as mock_wallet_get_public_did, async_mock.patch.object(
            test_module, "AnonCredsIssuer", async_mock.MagicMock()
        ) as mock_issuer, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_wallet_get_public_did.return_value = self.test_did_info

            mock_issuer.return_value = async_mock.MagicMock(
                create_and_register_schema=async_mock.CoroutineMock(
                    return_value=SchemaResult(
                        job_id=None,
                        registration_metadata=None,
                        schema_metadata={"seqNo": "1"},
                        schema_state=SchemaState(
                            state=SchemaState.STATE_FINISHED,
                            schema_id=SCHEMA_ID,
                            schema=AnonCredsSchema(
                                issuer_id="",
                                attr_names=["table", "drink", "colour"],
                                name="schema_name",
                                version="1.0",
                            ),
                        ),
                    )
                )
            )

            result = await test_module.schemas_send_schema(self.request)
            assert result == mock_response.return_value

            mock_response.assert_called_once_with(
                {
                    "sent": {
                        "schema_id": SCHEMA_ID,
                        "schema": {
                            "ver": "1.0",
                            "ident": SCHEMA_ID,
                            "name": "schema_name",
                            "version": "1.0",
                            "attr_names": ["table", "drink", "colour"],
                            "seqNo": "1",
                        },
                    },
                    "schema_id": SCHEMA_ID,
                    "schema": {
                        "ver": "1.0",
                        "ident": SCHEMA_ID,
                        "name": "schema_name",
                        "version": "1.0",
                        "attr_names": ["table", "drink", "colour"],
                        "seqNo": "1",
                    },
                }
            )

    @pytest.mark.skip(reason="anoncreds-rs/endorser breaking change")
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

    @pytest.mark.skip(reason="anoncreds-rs/endorser breaking change")
    async def test_send_schema_create_transaction_for_endorser_storage_x(
        self,
    ):
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

    @pytest.mark.skip(reason="anoncreds-rs/endorser breaking change")
    async def test_send_schema_create_transaction_for_endorser_not_found_x(
        self,
    ):
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

    @pytest.mark.skip(reason="anoncreds-rs/endorser breaking change")
    async def test_send_schema_create_transaction_for_endorser_base_model_x(
        self,
    ):
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

    @pytest.mark.skip(reason="anoncreds-rs/endorser breaking change")
    async def test_send_schema_create_transaction_for_endorser_no_endorser_info_x(
        self,
    ):
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

    @pytest.mark.skip(reason="anoncreds-rs/endorser breaking change")
    async def test_send_schema_create_transaction_for_endorser_no_endorser_did_x(
        self,
    ):
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

        with async_mock.patch.object(
            InMemoryWallet,
            "get_public_did",
        ) as mock_wallet_get_public_did, async_mock.patch.object(
            test_module, "AnonCredsIssuer", async_mock.MagicMock()
        ) as mock_issuer:
            mock_wallet_get_public_did.return_value = self.test_did_info
            mock_issuer.return_value = async_mock.MagicMock(
                create_and_register_schema=async_mock.CoroutineMock(
                    side_effect=AnonCredsResolutionError("No ledger available")
                )
            )

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

        with async_mock.patch.object(
            InMemoryWallet,
            "get_public_did",
        ) as mock_wallet_get_public_did, async_mock.patch.object(
            test_module, "AnonCredsIssuer", async_mock.MagicMock()
        ) as mock_issuer:
            mock_wallet_get_public_did.return_value = self.test_did_info
            mock_issuer.return_value = async_mock.MagicMock(
                create_and_register_schema=async_mock.CoroutineMock(
                    side_effect=AnonCredsIssuerError("Pretend LedgerError")
                )
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.schemas_send_schema(self.request)

    async def test_created(self):
        self.request.match_info = {"schema_id": SCHEMA_ID}

        with async_mock.patch.object(
            test_module, "AnonCredsIssuer", async_mock.MagicMock()
        ) as mock_issuer, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_issuer.return_value = async_mock.MagicMock(
                get_created_schemas=async_mock.CoroutineMock(return_value=[SCHEMA_ID])
            )

            result = await test_module.schemas_created(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with({"schema_ids": [SCHEMA_ID]})

    async def test_get_schema(self):
        self.request.match_info = {"schema_id": SCHEMA_ID}
        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.schemas_get_schema(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {
                    "ledger_id": "test_ledger_id",
                    "schema": {
                        "ver": "1.0",
                        "id": SCHEMA_ID,
                        "name": "schema_name",
                        "version": "1.0",
                        "attrNames": ["table", "drink", "colour"],
                        "seqNo": "1",
                    },
                }
            )

    async def test_get_schema_multitenant(self):
        self.profile_injector.bind_instance(
            BaseMultitenantManager,
            async_mock.MagicMock(MultitenantManager, autospec=True),
        )
        self.request.match_info = {"schema_id": SCHEMA_ID}
        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.schemas_get_schema(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {
                    "ledger_id": "test_ledger_id",
                    "schema": {
                        "ver": "1.0",
                        "id": SCHEMA_ID,
                        "name": "schema_name",
                        "version": "1.0",
                        "attrNames": ["table", "drink", "colour"],
                        "seqNo": "1",
                    },
                }
            )

    async def test_get_schema_on_seq_no(self):
        self.registry._resolver_for_identifier = async_mock.CoroutineMock(
            return_value=self.indy_ledger
        )
        self.indy_ledger.get_schema = async_mock.CoroutineMock(
            return_value=GetSchemaResult(
                schema=AnonCredsSchema(
                    issuer_id="",
                    attr_names=["table", "drink", "colour"],
                    name="schema_name",
                    version="1.0",
                ),
                schema_id=SCHEMA_ID,
                resolution_metadata={"ledger_id": None},
                schema_metadata={"seqNo": "1"},
            )
        )
        self.request.match_info = {"schema_id": "12345"}
        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.schemas_get_schema(self.request)
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {
                    "schema": {
                        "ver": "1.0",
                        "id": SCHEMA_ID,
                        "name": "schema_name",
                        "version": "1.0",
                        "attrNames": ["table", "drink", "colour"],
                        "seqNo": "1",
                    },
                }
            )

    async def test_get_schema_no_ledger(self):
        self.indy_ledger.get_schema = async_mock.CoroutineMock(
            side_effect=AnonCredsResolutionError("No ledger available")
        )
        self.request.match_info = {"schema_id": SCHEMA_ID}
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.schemas_get_schema(self.request)

    async def test_get_schema_x_ledger(self):
        self.indy_ledger.get_schema = async_mock.CoroutineMock(
            side_effect=AnonCredsResolutionError("Failed to retrieve schema")
        )
        self.request.match_info = {"schema_id": SCHEMA_ID}
        with self.assertRaises(test_module.web.HTTPForbidden):
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
