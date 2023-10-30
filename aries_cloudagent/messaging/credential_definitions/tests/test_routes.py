from anoncreds import CredentialDefinition
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
import pytest

from ....anoncreds.base import AnonCredsRegistrationError

from ....anoncreds.default.legacy_indy.registry import LegacyIndyRegistry
from ....anoncreds.issuer import AnonCredsIssuer
from ....anoncreds.models.anoncreds_cred_def import (
    CredDef,
    CredDefResult,
    CredDefState,
    CredDefValue,
    CredDefValuePrimary,
    GetCredDefResult,
)
from ....anoncreds.registry import AnonCredsRegistry
from ....askar.profile import AskarProfile

from ....wallet.did_info import DIDInfo
from ....wallet.did_method import SOV
from ....wallet.in_memory import InMemoryWallet
from ....wallet.key_type import ED25519
from unittest import IsolatedAsyncioTestCase
from aries_cloudagent.tests import mock

from ....admin.request_context import AdminRequestContext
from ....core.in_memory.profile import InMemoryProfile
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
CRED_DEF_ID = "WgWxqztrNooG92RXvxSTWv:3:CL:20:tag"


class TestCredentialDefinitionRoutes(IsolatedAsyncioTestCase):
    def setUp(self):
        self.session_inject = {}
        self.profile = InMemoryProfile.test_profile(profile_class=AskarProfile)
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

        self.issuer = AnonCredsIssuer(self.profile)
        self.profile_injector.bind_instance(AnonCredsIssuer, self.issuer)

        self.indy_ledger = LegacyIndyRegistry()

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
        )
        self.test_did = "55GkHamhTU1ZbTbV2ab9DE"
        self.test_did_info = DIDInfo(
            did=self.test_did,
            verkey="3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
            metadata={"test": "test"},
            method=SOV,
            key_type=ED25519,
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
                create_and_register_credential_definition=async_mock.CoroutineMock(
                    return_value=CredDefResult(
                        job_id=None,
                        registration_metadata=None,
                        credential_definition_metadata=None,
                        credential_definition_state=CredDefState(
                            state="finished",
                            credential_definition_id=CRED_DEF_ID,
                            credential_definition=None,
                        ),
                    )
                )
            )

            result = (
                await test_module.credential_definitions_send_credential_definition(
                    self.request
                )
            )
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {
                    "sent": {"credential_definition_id": CRED_DEF_ID},
                    "credential_definition_id": CRED_DEF_ID,
                }
            )

    @pytest.mark.skip(reason="anoncreds-rs/endorser breaking change")
    async def test_send_credential_definition_create_transaction_for_endorser(
        self,
    ):
        self.request.json = async_mock.CoroutineMock(
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
        ) as mock_conn_rec_retrieve, mock.patch.object(
            test_module, "TransactionManager", mock.MagicMock()
        ) as mock_txn_mgr, mock.patch.object(
            test_module.web, "json_response", mock.MagicMock()
        ) as mock_response:
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
            result = (
                await test_module.credential_definitions_send_credential_definition(
                    self.request
                )
            )
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {
                    "sent": {"credential_definition_id": CRED_DEF_ID},
                    "txn": {"...": "..."},
                }
            )

    @pytest.mark.skip(reason="anoncreds-rs/endorser breaking change")
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

        with mock.patch.object(
            ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve, mock.patch.object(
            test_module, "TransactionManager", mock.MagicMock()
        ) as mock_txn_mgr:
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

    @pytest.mark.skip(reason="anoncreds-rs/endorser breaking change")
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

    @pytest.mark.skip(reason="anoncreds-rs/endorser breaking change")
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

    @pytest.mark.skip(reason="anoncreds-rs/endorser breaking change")
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

    @pytest.mark.skip(reason="anoncreds-rs/endorser breaking change")
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

        self.indy_ledger_req_exec.get_ledger_for_identifier = async_mock.CoroutineMock(
            return_value=(None, None)
        )

        with async_mock.patch.object(
            InMemoryWallet,
            "get_public_did",
        ) as mock_wallet_get_public_did, async_mock.patch.object(
            CredentialDefinition, "create"
        ) as mock_cred_def_create, async_mock.patch.object(
            CredentialDefinition, "to_json"
        ) as mock_cred_def_json, async_mock.patch.object(
            CredDef, "from_native"
        ) as mock_cred_def_from_native:
            mock_wallet_get_public_did.return_value = self.test_did_info
            mock_cred_def_create.return_value = [
                CredentialDefinition(None),
                "CredentialDefinitionPrivate",
                "KeyCorrectnessProof",
            ]
            mock_cred_def_json.return_value = {}
            mock_cred_def_from_native.return_value = {}

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

        self.indy_ledger.register_credential_definition = async_mock.CoroutineMock(
            side_effect=AnonCredsRegistrationError("failed")
        )
        with async_mock.patch.object(
            InMemoryWallet,
            "get_public_did",
        ) as mock_wallet_get_public_did, async_mock.patch.object(
            CredentialDefinition, "create"
        ) as mock_cred_def_create, async_mock.patch.object(
            CredentialDefinition, "to_json"
        ) as mock_cred_def_json, async_mock.patch.object(
            CredDef, "from_native"
        ) as mock_cred_def_from_native:
            mock_wallet_get_public_did.return_value = self.test_did_info
            mock_cred_def_create.return_value = [
                CredentialDefinition(None),
                "CredentialDefinitionPrivate",
                "KeyCorrectnessProof",
            ]
            mock_cred_def_json.return_value = {}
            mock_cred_def_from_native.return_value = CredDef(
                issuer_id="issuer_id",
                schema_id=SCHEMA_ID,
                type="CL",
                tag="tag",
                value=None,
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.credential_definitions_send_credential_definition(
                    self.request
                )

    async def test_created(self):
        self.request.match_info = {"cred_def_id": CRED_DEF_ID}

        with async_mock.patch.object(
            test_module, "AnonCredsIssuer", async_mock.MagicMock()
        ) as mock_issuer:
            mock_issuer.return_value = async_mock.MagicMock(
                get_created_credential_definitions=async_mock.CoroutineMock(
                    return_value=[CRED_DEF_ID]
                )
            )

            with async_mock.patch.object(
                test_module.web, "json_response"
            ) as mock_response:
                result = await test_module.credential_definitions_created(self.request)
                assert result == mock_response.return_value
                mock_response.assert_called_once_with(
                    {"credential_definition_ids": [CRED_DEF_ID]}
                )

    async def test_get_credential_definition(self):
        self.registry.get_credential_definition = async_mock.CoroutineMock(
            return_value=GetCredDefResult(
                credential_definition_id=CRED_DEF_ID,
                resolution_metadata=None,
                credential_definition_metadata=None,
                credential_definition=CredDef(
                    issuer_id="test",
                    schema_id="test",
                    type="CL",
                    tag="test",
                    value=CredDefValue(
                        primary=CredDefValuePrimary(
                            n="n", s="s", r="r", rctxt="rctxt", z="z"
                        )
                    ),
                ),
            )
        )

        self.request.match_info = {"cred_def_id": CRED_DEF_ID}
        with mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.credential_definitions_get_credential_definition(
                self.request
            )
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {
                    "credential_definition": {
                        "ident": CRED_DEF_ID,
                        "schemaId": "test",
                        "typ": "CL",
                        "tag": "test",
                        "value": {
                            "primary": {
                                "n": "n",
                                "s": "s",
                                "r": "r",
                                "rctxt": "rctxt",
                                "z": "z",
                            }
                        },
                    },
                }
            )

    async def test_get_credential_definition_multitenant(self):
        self.profile_injector.bind_instance(
            BaseMultitenantManager,
            mock.MagicMock(MultitenantManager, autospec=True),
        )
        self.registry.get_credential_definition = async_mock.CoroutineMock(
            return_value=GetCredDefResult(
                credential_definition_id=CRED_DEF_ID,
                resolution_metadata=None,
                credential_definition_metadata=None,
                credential_definition=CredDef(
                    issuer_id="test",
                    schema_id="test",
                    type="CL",
                    tag="test",
                    value=CredDefValue(
                        primary=CredDefValuePrimary(
                            n="n", s="s", r="r", rctxt="rctxt", z="z"
                        )
                    ),
                ),
            )
        )
        self.request.match_info = {"cred_def_id": CRED_DEF_ID}
        with async_mock.patch.object(test_module.web, "json_response") as mock_response:
            result = await test_module.credential_definitions_get_credential_definition(
                self.request
            )
            assert result == mock_response.return_value
            mock_response.assert_called_once_with(
                {
                    "credential_definition": {
                        "ident": CRED_DEF_ID,
                        "schemaId": "test",
                        "typ": "CL",
                        "tag": "test",
                        "value": {
                            "primary": {
                                "n": "n",
                                "s": "s",
                                "r": "r",
                                "rctxt": "rctxt",
                                "z": "z",
                            }
                        },
                    },
                }
            )

    async def test_get_credential_definition_no_ledger(self):
        self.profile_injector.bind_instance(
            IndyLedgerRequestsExecutor,
            mock.MagicMock(
                get_ledger_for_identifier=mock.CoroutineMock(return_value=(None, None))
            ),
        )

        self.request.match_info = {"cred_def_id": CRED_DEF_ID}
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
