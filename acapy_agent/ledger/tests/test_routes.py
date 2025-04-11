import json
import uuid
from typing import Optional
from unittest import IsolatedAsyncioTestCase

import pytest
from marshmallow import ValidationError
from uuid_utils import uuid4

from ...connections.models.conn_record import ConnRecord
from ...ledger.base import BaseLedger
from ...ledger.endpoint_type import EndpointType
from ...ledger.multiple_ledger.base_manager import BaseMultipleLedgerManager
from ...ledger.multiple_ledger.ledger_config_schema import (
    ConfigurableWriteLedgersSchema,
    LedgerConfigInstanceSchema,
    LedgerConfigListSchema,
)
from ...ledger.multiple_ledger.ledger_requests_executor import IndyLedgerRequestsExecutor
from ...multitenant.base import BaseMultitenantManager
from ...multitenant.manager import MultitenantManager
from ...tests import mock
from ...utils.testing import create_test_profile
from .. import routes as test_module
from ..indy_vdr import Role


class TestLedgerRoutes(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.ledger = mock.create_autospec(BaseLedger)
        self.ledger.pool_name = "pool.0"
        self.profile = await create_test_profile(
            settings={
                "admin.admin_api_key": "secret-key",
            }
        )
        self.context = self.profile.context
        setattr(self.context, "profile", self.profile)
        self.profile.context.injector.bind_instance(BaseLedger, self.ledger)
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

        self.test_did = "did"
        self.test_verkey = "verkey"
        self.test_endpoint = "http://localhost:8021"
        self.test_endpoint_type = EndpointType.PROFILE
        self.test_endpoint_type_profile = "http://company.com/profile"
        self.mock_ledger_requests_executor = mock.MagicMock(
            IndyLedgerRequestsExecutor, autospec=True
        )

    async def test_missing_ledger(self):
        self.mock_ledger_requests_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=(None, None)
        )
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            self.mock_ledger_requests_executor,
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
        self.mock_ledger_requests_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=(None, self.ledger)
        )
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            self.mock_ledger_requests_executor,
        )
        self.request.query = {"did": self.test_did}
        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            self.ledger.get_key_for_did.return_value = self.test_verkey
            result = await test_module.get_did_verkey(self.request)
            json_response.assert_called_once_with(
                {"verkey": self.ledger.get_key_for_did.return_value}
            )
            assert result is json_response.return_value

    async def test_get_verkey_b(self):
        self.mock_ledger_requests_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=("test_ledger_id", self.ledger)
        )
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            self.mock_ledger_requests_executor,
        )
        self.request.query = {"did": self.test_did}
        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
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
            mock.MagicMock(MultitenantManager, autospec=True),
        )
        self.request.query = {"did": self.test_did}
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            self.mock_ledger_requests_executor,
        )
        with (
            mock.patch.object(
                IndyLedgerRequestsExecutor,
                "get_ledger_for_identifier",
                mock.CoroutineMock(return_value=("test_ledger_id", self.ledger)),
            ),
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as json_response,
        ):
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
        self.mock_ledger_requests_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=("test_ledger_id", self.ledger)
        )
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            self.mock_ledger_requests_executor,
        )

        self.request.query = {"did": self.test_did}
        self.ledger.get_key_for_did.return_value = None
        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.get_did_verkey(self.request)

    async def test_get_verkey_x(self):
        self.mock_ledger_requests_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=(None, self.ledger)
        )
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            self.mock_ledger_requests_executor,
        )
        self.request.query = {"did": self.test_did}
        self.ledger.get_key_for_did.side_effect = test_module.LedgerError()
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.get_did_verkey(self.request)

    async def test_get_endpoint(self):
        self.mock_ledger_requests_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=(None, self.ledger)
        )
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            self.mock_ledger_requests_executor,
        )
        self.request.query = {"did": self.test_did}
        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
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
            mock.MagicMock(MultitenantManager, autospec=True),
        )
        self.request.query = {"did": self.test_did}
        with (
            mock.patch.object(
                IndyLedgerRequestsExecutor,
                "get_ledger_for_identifier",
                mock.CoroutineMock(return_value=("test_ledger_id", self.ledger)),
            ),
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as json_response,
        ):
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
        self.mock_ledger_requests_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=("test_ledger_id", self.ledger)
        )
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            self.mock_ledger_requests_executor,
        )

        self.request.query = {
            "did": self.test_did,
            "endpoint_type": self.test_endpoint_type.w3c,
        }
        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
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
        self.mock_ledger_requests_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=("test_ledger_id", self.ledger)
        )
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            self.mock_ledger_requests_executor,
        )

        self.request.query = {"did": self.test_did}
        self.ledger.get_endpoint_for_did.side_effect = test_module.LedgerError()
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.get_did_endpoint(self.request)

    async def test_register_nym(self):
        self.request.query = {
            "did": self.test_did,
            "verkey": self.test_verkey,
            "role": "reset",
        }
        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            success: bool = True
            txn: Optional[dict] = None
            self.ledger.register_nym.return_value = (success, txn)
            result = await test_module.register_ledger_nym(self.request)
            json_response.assert_called_once_with({"success": success})
            assert result is json_response.return_value

    async def test_register_nym_bad_request(self):
        self.request.query = {"no": "did"}
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.register_ledger_nym(self.request)

    async def test_register_nym_ledger_txn_error(self):
        self.request.query = {"did": self.test_did, "verkey": self.test_verkey}
        self.ledger.register_nym.side_effect = test_module.LedgerTransactionError("Error")
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
            self.ledger.register_nym.return_value = (
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
            self.ledger.register_nym.return_value = (
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

        with (
            mock.patch.object(
                ConnRecord, "retrieve_by_id", mock.CoroutineMock()
            ) as mock_conn_rec_retrieve,
            mock.patch.object(
                test_module, "TransactionManager", mock.MagicMock()
            ) as mock_txn_mgr,
        ):
            mock_txn_mgr.return_value = mock.MagicMock(
                create_record=mock.CoroutineMock(side_effect=test_module.StorageError())
            )
            mock_conn_rec_retrieve.return_value = mock.MagicMock(
                metadata_get=mock.CoroutineMock(
                    return_value={
                        "endorser_did": ("did"),
                        "endorser_name": ("name"),
                    }
                )
            )
            self.ledger.register_nym.return_value = (
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

        with mock.patch.object(
            ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve:
            mock_conn_rec_retrieve.side_effect = test_module.StorageNotFoundError()
            self.ledger.register_nym.return_value = (
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

        with mock.patch.object(
            ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve:
            mock_conn_rec_retrieve.side_effect = test_module.BaseModelError()
            self.ledger.register_nym.return_value = (
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

        with mock.patch.object(
            ConnRecord, "retrieve_by_id", mock.CoroutineMock()
        ) as mock_conn_rec_retrieve:
            mock_conn_rec_retrieve.return_value = mock.MagicMock(
                metadata_get=mock.CoroutineMock(return_value=None)
            )
            self.ledger.register_nym.return_value = (
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
            self.ledger.register_nym.return_value = (
                True,
                {"signed_txn": {"...": "..."}},
            )

            with self.assertRaises(test_module.web.HTTPForbidden):
                await test_module.register_ledger_nym(self.request)

    async def test_get_nym_role_a(self):
        self.mock_ledger_requests_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=(None, self.ledger)
        )
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            self.mock_ledger_requests_executor,
        )

        self.request.query = {"did": self.test_did}

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            self.ledger.get_nym_role.return_value = Role.USER
            result = await test_module.get_nym_role(self.request)
            json_response.assert_called_once_with({"role": "USER"})
            assert result is json_response.return_value

    async def test_get_nym_role_b(self):
        self.mock_ledger_requests_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=("test_ledger_id", self.ledger)
        )
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            self.mock_ledger_requests_executor,
        )

        self.request.query = {"did": self.test_did}

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
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
            mock.MagicMock(MultitenantManager, autospec=True),
        )
        self.request.query = {"did": self.test_did}

        with (
            mock.patch.object(
                IndyLedgerRequestsExecutor,
                "get_ledger_for_identifier",
                mock.CoroutineMock(return_value=("test_ledger_id", self.ledger)),
            ),
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as json_response,
        ):
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
        self.mock_ledger_requests_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=("test_ledger_id", self.ledger)
        )
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            self.mock_ledger_requests_executor,
        )
        self.request.query = {"did": self.test_did}
        self.ledger.get_nym_role.side_effect = test_module.LedgerTransactionError(
            "Error in building get-nym request"
        )
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.get_nym_role(self.request)

    async def test_get_nym_role_bad_ledger_req(self):
        self.mock_ledger_requests_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=("test_ledger_id", self.ledger)
        )
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            self.mock_ledger_requests_executor,
        )
        self.request.query = {"did": self.test_did}
        self.ledger.get_nym_role.side_effect = test_module.BadLedgerRequestError(
            "No such public DID"
        )
        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.get_nym_role(self.request)

    async def test_get_nym_role_ledger_error(self):
        self.mock_ledger_requests_executor.get_ledger_for_identifier = mock.CoroutineMock(
            return_value=(None, self.ledger)
        )
        self.profile.context.injector.bind_instance(
            IndyLedgerRequestsExecutor,
            self.mock_ledger_requests_executor,
        )
        self.request.query = {"did": self.test_did}
        self.ledger.get_nym_role.side_effect = test_module.LedgerError("Error")
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.get_nym_role(self.request)

    async def test_rotate_public_did_keypair(self):
        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            self.ledger.rotate_public_did_keypair = mock.CoroutineMock()

            await test_module.rotate_public_did_keypair(self.request)
            json_response.assert_called_once_with({})

    async def test_rotate_public_did_keypair_public_wallet_x(self):
        with mock.patch.object(test_module.web, "json_response", mock.Mock()):
            self.ledger.rotate_public_did_keypair = mock.CoroutineMock(
                side_effect=test_module.WalletError("Exception")
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.rotate_public_did_keypair(self.request)

    async def test_get_taa(self):
        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
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

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
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
        self.request.json = mock.CoroutineMock(
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
        self.request.json = mock.CoroutineMock(
            return_value={
                "version": "version",
                "text": "text",
                "mechanism": "mechanism",
            }
        )

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
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
        self.request.json = mock.CoroutineMock(
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
        mock_app = mock.MagicMock()
        mock_app.add_routes = mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]

    async def test_get_write_ledger(self):
        mock_manager = mock.MagicMock(BaseMultipleLedgerManager, autospec=True)
        mock_manager.get_ledger_id_by_ledger_pool_name = mock.CoroutineMock(
            return_value="test_ledger_id"
        )
        self.profile.context.injector.bind_instance(
            BaseMultipleLedgerManager, mock_manager
        )
        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            result = await test_module.get_write_ledger(self.request)
            json_response.assert_called_once_with(
                {
                    "ledger_id": "test_ledger_id",
                }
            )
            assert result is json_response.return_value

    async def test_get_write_ledger_single_ledger(self):
        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            result = await test_module.get_write_ledger(self.request)
            json_response.assert_called_once_with(
                {
                    "ledger_id": "default",
                }
            )
            assert result is json_response.return_value

    async def test_get_ledger_config(self):
        mock_manager = mock.MagicMock(BaseMultipleLedgerManager, autospec=True)
        mock_manager.get_prod_ledgers = mock.CoroutineMock(
            return_value={
                "test_1": mock.MagicMock(),
                "test_2": mock.MagicMock(),
                "test_5": mock.MagicMock(),
            }
        )
        mock_manager.get_nonprod_ledgers = mock.CoroutineMock(
            return_value={
                "test_3": mock.MagicMock(),
                "test_4": mock.MagicMock(),
            }
        )
        self.profile.context.injector.bind_instance(
            BaseMultipleLedgerManager, mock_manager
        )

        self.context.settings["ledger.ledger_config_list"] = [
            {"id": "test_1", "genesis_transactions": "..."},
            {"id": "test_2", "genesis_transactions": "..."},
            {"id": "test_3", "genesis_transactions": "..."},
            {"id": "test_4", "genesis_transactions": "..."},
        ]
        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
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
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.get_ledger_config(self.request)

    async def test_get_ledger_config_structure(self):
        """Test the structure of the ledger config response."""
        mock_manager = mock.MagicMock(BaseMultipleLedgerManager, autospec=True)
        mock_manager.get_prod_ledgers = mock.CoroutineMock(return_value={"test_1": None})
        mock_manager.get_nonprod_ledgers = mock.CoroutineMock(
            return_value={"test_2": None}
        )
        self.profile.context.injector.bind_instance(
            BaseMultipleLedgerManager, mock_manager
        )

        self.context.settings["ledger.ledger_config_list"] = [
            {
                "id": "test_1",
                "is_production": True,
                "is_write": True,
                "keepalive": 5,
                "read_only": False,
                "pool_name": "test_pool",
                "socks_proxy": None,
            },
            {
                "id": "test_2",
                "is_production": False,
                "is_write": False,
                "keepalive": 10,
                "read_only": True,
                "pool_name": "non_prod_pool",
                "socks_proxy": None,
            },
        ]

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            await test_module.get_ledger_config(self.request)

            response_data = json_response.call_args[0][0]
            assert "production_ledgers" in response_data
            assert "non_production_ledgers" in response_data

            prod_ledger = response_data["production_ledgers"][0]
            assert prod_ledger == {
                "id": "test_1",
                "is_production": True,
                "is_write": True,
                "keepalive": 5,
                "read_only": False,
                "pool_name": "test_pool",
                "socks_proxy": None,
            }

            non_prod_ledger = response_data["non_production_ledgers"][0]
            assert non_prod_ledger == {
                "id": "test_2",
                "is_production": False,
                "is_write": False,
                "keepalive": 10,
                "read_only": True,
                "pool_name": "non_prod_pool",
                "socks_proxy": None,
            }

    async def test_ledger_config_schema_validation(self):
        """Test schema validation for required fields."""
        schema = LedgerConfigInstanceSchema()

        minimal_data = {
            "is_production": True,
            "is_write": False,
            "keepalive": 5,
            "read_only": False,
        }
        loaded = schema.load(minimal_data)
        assert loaded.pool_name == loaded.id
        assert loaded.is_write is False

        with pytest.raises(ValidationError) as exc:
            schema.load({"is_production": "not_bool"})
        assert "is_production" in exc.value.messages

    async def test_ledger_config_id_generation(self):
        """Test automatic ID generation when missing."""
        schema = LedgerConfigInstanceSchema()

        data = {
            "is_production": True,
            "is_write": False,  # Add required fields
            "keepalive": 5,
            "read_only": False,
        }
        loaded = schema.load(data)
        assert uuid.UUID(loaded.id, version=4)

        explicit_id = str(uuid4())
        loaded = schema.load({"id": explicit_id, "is_production": True})
        assert loaded.id == explicit_id

    async def test_empty_ledger_lists(self):
        schema = LedgerConfigListSchema()
        empty_data = {"production_ledgers": [], "non_production_ledgers": []}
        loaded = schema.load(empty_data)
        assert loaded == empty_data

    # Multiple Ledgers Configured
    async def test_get_write_ledgers_multiple(self):
        # Mock the multiple ledger manager
        mock_manager = mock.MagicMock(BaseMultipleLedgerManager)
        mock_manager.get_write_ledgers = mock.CoroutineMock(
            return_value=["ledger1", "ledger2", "ledger3"]
        )
        self.profile.context.injector.bind_instance(
            BaseMultipleLedgerManager, mock_manager
        )

        with mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as json_response:
            result = await test_module.get_write_ledgers(self.request)

            # Assert the response matches the expected structure
            json_response.assert_called_once_with(
                {"write_ledgers": ["ledger1", "ledger2", "ledger3"]}
            )
            assert result is json_response.return_value

    # Single Ledger (No Multi-Ledger Manager)
    async def test_get_write_ledgers_single(self):
        # Ensure no multi-ledger manager is bound
        self.profile.context.injector.clear_binding(BaseMultipleLedgerManager)

        result = await test_module.get_write_ledgers(self.request)

        # Extract the JSON body from the response
        response_body = result.text
        response_body = json.loads(response_body)

        # Assert the response is correct
        self.assertEqual(response_body, {"write_ledgers": ["default"]})

    # Schema Validation
    async def test_get_write_ledgers_schema(self):
        # Mock the multiple ledger manager
        mock_manager = mock.MagicMock(BaseMultipleLedgerManager)
        mock_manager.get_write_ledgers = mock.CoroutineMock(
            return_value=["ledger1", "ledger2"]
        )
        self.profile.context.injector.bind_instance(
            BaseMultipleLedgerManager, mock_manager
        )

        response = await test_module.get_write_ledgers(self.request)

        # Validate against the schema
        schema = ConfigurableWriteLedgersSchema()
        data = json.loads(response.body)
        validated = schema.validate(data)
        assert validated == {}
