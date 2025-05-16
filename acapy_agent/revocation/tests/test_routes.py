import os
import shutil
import unittest
import pytest
from aiohttp.web import HTTPBadRequest, HTTPNotFound

from ...admin.request_context import AdminRequestContext
from ...ledger.base import BaseLedger
from ...ledger.multiple_ledger.base_manager import BaseMultipleLedgerManager
from ...protocols.endorse_transaction.v1_0.manager import (
    TransactionManager,
    TransactionManagerError,
)
from ...protocols.endorse_transaction.v1_0.models.transaction_record import (
    TransactionRecord,
)
from ...revocation.error import RevocationError
from ...storage.askar import AskarStorage
from ...storage.base import BaseStorage
from ...storage.error import StorageError
from ...tests import mock
from ...utils.testing import create_test_profile
from .. import routes as test_module
from ..manager import RevocationManager
from ..models.issuer_rev_reg_record import IssuerRevRegRecord
from multidict import MultiDict
import json


class TestRevocationRoutes(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = await create_test_profile(
            settings={
                "admin.admin_api_key": "secret-key",
            }
        )
        self.context = AdminRequestContext.test_context({}, self.profile)
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

        self.test_did = "sample-did"

        self.author_profile = await create_test_profile(
            settings={
                "admin.admin_api_key": "author-key",
            }
        )
        self.author_profile.settings.set_value("endorser.author", True)
        self.author_context = AdminRequestContext.test_context({}, self.author_profile)
        self.author_request_dict = {
            "context": self.author_context,
            "outbound_message_router": mock.CoroutineMock(),
        }
        self.author_request = mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.author_request_dict[k],
            headers={"x-api-key": "author-key"},
        )

    async def test_validate_cred_rev_rec_qs_and_revoke_req(self):
        for req in (
            test_module.CredRevRecordQueryStringSchema(),
            test_module.RevokeRequestSchema(),
        ):
            req.validate_fields(
                {
                    "rev_reg_id": test_module.INDY_REV_REG_ID_EXAMPLE,
                    "cred_rev_id": test_module.INDY_CRED_REV_ID_EXAMPLE,
                }
            )
            req.validate_fields({"cred_ex_id": test_module.UUID4_EXAMPLE})
            with self.assertRaises(test_module.ValidationError):
                req.validate_fields({})
            with self.assertRaises(test_module.ValidationError):
                req.validate_fields({"rev_reg_id": test_module.INDY_REV_REG_ID_EXAMPLE})
            with self.assertRaises(test_module.ValidationError):
                req.validate_fields({"cred_rev_id": test_module.INDY_CRED_REV_ID_EXAMPLE})
            with self.assertRaises(test_module.ValidationError):
                req.validate_fields(
                    {
                        "rev_reg_id": test_module.INDY_REV_REG_ID_EXAMPLE,
                        "cred_ex_id": test_module.UUID4_EXAMPLE,
                    }
                )
            with self.assertRaises(test_module.ValidationError):
                req.validate_fields(
                    {
                        "cred_rev_id": test_module.INDY_CRED_REV_ID_EXAMPLE,
                        "cred_ex_id": test_module.UUID4_EXAMPLE,
                    }
                )
            with self.assertRaises(test_module.ValidationError):
                req.validate_fields(
                    {
                        "rev_reg_id": test_module.INDY_REV_REG_ID_EXAMPLE,
                        "cred_rev_id": test_module.INDY_CRED_REV_ID_EXAMPLE,
                        "cred_ex_id": test_module.UUID4_EXAMPLE,
                    }
                )

    async def test_revoke(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "rev_reg_id": "rr_id",
                "cred_rev_id": "23",
                "publish": "false",
            }
        )

        with (
            mock.patch.object(
                test_module, "RevocationManager", autospec=True
            ) as mock_mgr,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_mgr.return_value.revoke_credential = mock.CoroutineMock()

            await test_module.revoke(self.request)

            mock_response.assert_called_once_with({})

    async def test_revoke_endorser_no_conn_id_by_cred_ex_id(self):
        self.author_request.json = mock.CoroutineMock(
            return_value={
                "rev_reg_id": "rr_id",
                "cred_rev_id": "23",
                "publish": "false",
            }
        )

        with (
            mock.patch.object(
                test_module, "RevocationManager", autospec=True
            ) as mock_mgr,
            mock.patch.object(
                test_module,
                "get_endorser_connection_id",
                mock.CoroutineMock(return_value="dummy-conn-id"),
            ),
            mock.patch.object(test_module.web, "json_response"),
            mock.patch.object(TransactionManager, "create_record", mock.CoroutineMock()),
        ):
            mock_mgr.return_value.revoke_credential = mock.CoroutineMock(
                return_value={"result": "..."}
            )

            await test_module.revoke(self.author_request)

    async def test_revoke_endorser_by_cred_ex_id(self):
        self.author_request.json = mock.CoroutineMock(
            return_value={
                "rev_reg_id": "rr_id",
                "cred_rev_id": "23",
                "publish": "false",
                "connection_id": "dummy-conn-id",
                "cred_ex_id": "dummy-cxid",
            }
        )

        with (
            mock.patch.object(
                test_module, "RevocationManager", autospec=True
            ) as mock_mgr,
            mock.patch.object(test_module.web, "json_response"),
            mock.patch.object(
                test_module,
                "get_endorser_connection_id",
                mock.CoroutineMock(return_value="test_conn_id"),
            ),
            mock.patch.object(TransactionManager, "create_record", mock.CoroutineMock()),
        ):
            mock_mgr.return_value.revoke_credential = mock.CoroutineMock(
                return_value={"result": "..."}
            )

            await test_module.revoke(self.author_request)

    async def test_revoke_endorser_no_conn_id(self):
        self.author_request.json = mock.CoroutineMock(
            return_value={
                "rev_reg_id": "rr_id",
                "cred_rev_id": "23",
                "publish": "false",
            }
        )

        with (
            mock.patch.object(
                test_module, "RevocationManager", autospec=True
            ) as mock_mgr,
            mock.patch.object(
                test_module,
                "get_endorser_connection_id",
                mock.CoroutineMock(return_value=None),
            ),
            mock.patch.object(test_module.web, "json_response"),
            mock.patch.object(TransactionManager, "create_record", mock.CoroutineMock()),
        ):
            mock_mgr.return_value.revoke_credential = mock.CoroutineMock(
                return_value={"result": "..."}
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.revoke(self.author_request)

    async def test_revoke_endorser(self):
        self.author_request.json = mock.CoroutineMock(
            return_value={
                "rev_reg_id": "rr_id",
                "cred_rev_id": "23",
                "publish": "false",
                "connection_id": "dummy-conn-id",
            }
        )

        with (
            mock.patch.object(
                test_module, "RevocationManager", autospec=True
            ) as mock_mgr,
            mock.patch.object(test_module.web, "json_response"),
            mock.patch.object(
                test_module,
                "get_endorser_connection_id",
                mock.CoroutineMock(return_value="test_conn_id"),
            ),
            mock.patch.object(TransactionManager, "create_record", mock.CoroutineMock()),
        ):
            mock_mgr.return_value.revoke_credential = mock.CoroutineMock(
                return_value={"result": "..."}
            )

            await test_module.revoke(self.author_request)

    async def test_revoke_endorser_x(self):
        self.author_request.json = mock.CoroutineMock(
            return_value={
                "rev_reg_id": "rr_id",
                "cred_rev_id": "23",
                "publish": "false",
            }
        )

        with (
            mock.patch.object(
                test_module, "RevocationManager", autospec=True
            ) as mock_mgr,
            mock.patch.object(
                test_module,
                "get_endorser_connection_id",
                mock.CoroutineMock(return_value=None),
            ),
        ):
            mock_mgr.return_value.revoke_credential = mock.CoroutineMock()
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.revoke(self.author_request)

    async def test_revoke_by_cred_ex_id(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "cred_ex_id": "dummy-cxid",
                "publish": "false",
            }
        )

        with (
            mock.patch.object(
                test_module, "RevocationManager", autospec=True
            ) as mock_mgr,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            mock_mgr.return_value.revoke_credential = mock.CoroutineMock()

            await test_module.revoke(self.request)

            mock_response.assert_called_once_with({})

    async def test_revoke_not_found(self):
        self.request.json = mock.CoroutineMock(
            return_value={
                "rev_reg_id": "rr_id",
                "cred_rev_id": "23",
                "publish": "false",
            }
        )

        with (
            mock.patch.object(
                test_module, "RevocationManager", autospec=True
            ) as mock_mgr,
            mock.patch.object(test_module.web, "json_response"),
        ):
            mock_mgr.return_value.revoke_credential = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.revoke(self.request)

    async def test_publish_revocations(self):
        self.request.json = mock.CoroutineMock()

        with (
            mock.patch.object(
                test_module, "RevocationManager", autospec=True
            ) as mock_mgr,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            pub_pending = mock.CoroutineMock()
            mock_mgr.return_value.publish_pending_revocations = mock.CoroutineMock(
                return_value=({}, pub_pending.return_value)
            )

            await test_module.publish_revocations(self.request)

            mock_response.assert_called_once_with({"rrid2crid": pub_pending.return_value})

    async def test_publish_revocations_x(self):
        self.request.json = mock.CoroutineMock()

        with mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr:
            pub_pending = mock.CoroutineMock(side_effect=test_module.RevocationError())
            mock_mgr.return_value.publish_pending_revocations = pub_pending

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.publish_revocations(self.request)

    async def test_publish_revocations_endorser(self):
        self.author_request.json = mock.CoroutineMock(return_value={})

        with (
            mock.patch.object(
                test_module, "RevocationManager", autospec=True
            ) as mock_mgr,
            mock.patch.object(
                test_module,
                "get_endorser_connection_id",
                mock.CoroutineMock(return_value="dummy-conn-id"),
            ),
            mock.patch.object(
                TransactionManager,
                "create_record",
                mock.CoroutineMock(return_value=TransactionRecord()),
            ),
            mock.patch.object(
                TransactionManager,
                "create_request",
                mock.CoroutineMock(),
            ),
        ):
            pub_pending = mock.CoroutineMock()
            mock_mgr.return_value.publish_pending_revocations = mock.CoroutineMock(
                return_value=(
                    [
                        {"result": "..."},
                        {"result": "..."},
                    ],
                    pub_pending.return_value,
                )
            )

            result = await test_module.publish_revocations(self.author_request)
            assert result.status == 200

            # Auto endorsement
            self.author_request_dict["context"].settings["endorser.auto_request"] = True
            self.author_request = mock.MagicMock(
                app={},
                match_info={},
                query={},
                __getitem__=lambda _, k: self.author_request_dict[k],
                headers={"x-api-key": "author-key"},
            )
            self.author_request.json = mock.CoroutineMock()
            result = await test_module.publish_revocations(self.author_request)
            assert result.status == 200

    async def test_publish_revocations_endorser_exceptions(self):
        self.author_request.json = mock.CoroutineMock(return_value={})
        with mock.patch.object(
            test_module, "TransactionManager", autospec=True
        ) as mock_txn_mgr:
            mock_txn_mgr.return_value.create_record = mock.CoroutineMock(
                side_effect=StorageError()
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.publish_revocations(self.author_request)

        with mock.patch.object(
            test_module, "TransactionManager", autospec=True
        ) as mock_txn_mgr:
            mock_txn_mgr.return_value.create_request = mock.CoroutineMock(
                side_effect=[StorageError(), TransactionManagerError()]
            )
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.publish_revocations(self.author_request)
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.publish_revocations(self.author_request)

    async def test_publish_revocations_endorser_x(self):
        self.author_request.json = mock.CoroutineMock()

        with (
            mock.patch.object(
                test_module, "RevocationManager", autospec=True
            ) as mock_mgr,
            mock.patch.object(
                test_module,
                "get_endorser_connection_id",
                mock.CoroutineMock(return_value=None),
            ),
            mock.patch.object(test_module.web, "json_response"),
        ):
            pub_pending = mock.CoroutineMock()
            mock_mgr.return_value.publish_pending_revocations = mock.CoroutineMock(
                return_value=(
                    [
                        {"result": "..."},
                        {"result": "..."},
                    ],
                    pub_pending.return_value,
                )
            )
            pub_pending = mock.CoroutineMock()
            mock_mgr.return_value.publish_pending_revocations = pub_pending
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.publish_revocations(self.author_request)

    async def test_clear_pending_revocations(self):
        self.request.json = mock.CoroutineMock()

        with (
            mock.patch.object(
                test_module, "RevocationManager", autospec=True
            ) as mock_mgr,
            mock.patch.object(test_module.web, "json_response") as mock_response,
        ):
            clear_pending = mock.CoroutineMock()
            mock_mgr.return_value.clear_pending_revocations = clear_pending

            await test_module.clear_pending_revocations(self.request)

            mock_response.assert_called_once_with(
                {"rrid2crid": clear_pending.return_value}
            )

    async def test_clear_pending_revocations_x(self):
        self.request.json = mock.CoroutineMock()

        with (
            mock.patch.object(
                test_module, "RevocationManager", autospec=True
            ) as mock_mgr,
            mock.patch.object(test_module.web, "json_response"),
        ):
            clear_pending = mock.CoroutineMock(side_effect=test_module.StorageError())
            mock_mgr.return_value.clear_pending_revocations = clear_pending

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.clear_pending_revocations(self.request)

    async def test_create_rev_reg(self):
        CRED_DEF_ID = f"{self.test_did}:3:CL:1234:default"
        self.request.json = mock.CoroutineMock(
            return_value={
                "max_cred_num": "1000",
                "credential_definition_id": CRED_DEF_ID,
            }
        )

        with (
            mock.patch.object(AskarStorage, "find_all_records"),
            mock.patch.object(
                test_module, "IndyRevocation", autospec=True
            ) as mock_indy_revoc,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_indy_revoc.return_value = mock.MagicMock(
                init_issuer_registry=mock.CoroutineMock(
                    return_value=mock.MagicMock(
                        generate_registry=mock.CoroutineMock(),
                        serialize=mock.MagicMock(return_value="dummy"),
                    )
                )
            )

            result = await test_module.create_rev_reg(self.request)
            mock_json_response.assert_called_once_with({"result": "dummy"})
            assert result is mock_json_response.return_value

    async def test_create_rev_reg_no_such_cred_def(self):
        CRED_DEF_ID = f"{self.test_did}:3:CL:1234:default"
        self.request.json = mock.CoroutineMock(
            return_value={
                "max_cred_num": "1000",
                "credential_definition_id": CRED_DEF_ID,
            }
        )

        with (
            mock.patch.object(
                BaseStorage, "find_all_records", autospec=True
            ) as mock_find,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_find.return_value = False

            with self.assertRaises(HTTPNotFound):
                await test_module.create_rev_reg(self.request)
            mock_json_response.assert_not_called()

    async def test_create_rev_reg_no_revo_support(self):
        CRED_DEF_ID = f"{self.test_did}:3:CL:1234:default"
        self.request.json = mock.CoroutineMock(
            return_value={
                "max_cred_num": "1000",
                "credential_definition_id": CRED_DEF_ID,
            }
        )

        with (
            mock.patch.object(
                AskarStorage, "find_all_records", autospec=True
            ) as mock_find,
            mock.patch.object(
                test_module, "IndyRevocation", autospec=True
            ) as mock_indy_revoc,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_find.return_value = True
            mock_indy_revoc.return_value = mock.MagicMock(
                init_issuer_registry=mock.CoroutineMock(
                    side_effect=test_module.RevocationNotSupportedError(
                        error_code="dummy"
                    )
                )
            )

            with self.assertRaises(HTTPBadRequest):
                await test_module.create_rev_reg(self.request)

            mock_json_response.assert_not_called()

    async def test_rev_regs_created(self):
        CRED_DEF_ID = f"{self.test_did}:3:CL:1234:default"
        self.request.query = {
            "cred_def_id": CRED_DEF_ID,
            "state": test_module.IssuerRevRegRecord.STATE_ACTIVE,
        }

        with (
            mock.patch.object(
                test_module.IssuerRevRegRecord, "query", mock.CoroutineMock()
            ) as mock_query,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_query.return_value = [mock.MagicMock(revoc_reg_id="dummy")]

            result = await test_module.rev_regs_created(self.request)
            mock_json_response.assert_called_once_with({"rev_reg_ids": ["dummy"]})
            assert result is mock_json_response.return_value

    async def test_get_rev_reg(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with (
            mock.patch.object(
                test_module, "IndyRevocation", autospec=True
            ) as mock_indy_revoc,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    return_value=mock.MagicMock(
                        serialize=mock.MagicMock(return_value="dummy")
                    )
                )
            )

            result = await test_module.get_rev_reg(self.request)
            mock_json_response.assert_called_once_with({"result": "dummy"})
            assert result is mock_json_response.return_value

    async def test_get_rev_reg_not_found(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with (
            mock.patch.object(
                test_module, "IndyRevocation", autospec=True
            ) as mock_indy_revoc,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(error_code="dummy")
                )
            )

            with self.assertRaises(HTTPNotFound):
                await test_module.get_rev_reg(self.request)
            mock_json_response.assert_not_called()

    async def test_get_rev_reg_issued(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with (
            mock.patch.object(
                test_module.IssuerRevRegRecord,
                "retrieve_by_revoc_reg_id",
                mock.CoroutineMock(),
            ),
            mock.patch.object(
                test_module.IssuerCredRevRecord,
                "query_by_ids",
                mock.CoroutineMock(),
            ) as mock_query,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_query.return_value = [{"...": "..."}, {"...": "..."}]
            result = await test_module.get_rev_reg_issued_count(self.request)

            mock_json_response.assert_called_once_with({"result": 2})
            assert result is mock_json_response.return_value

    async def test_get_rev_reg_issued_x(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with mock.patch.object(
            test_module.IssuerRevRegRecord,
            "retrieve_by_revoc_reg_id",
            mock.CoroutineMock(),
        ) as mock_retrieve:
            mock_retrieve.side_effect = test_module.StorageNotFoundError("no such rec")

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.get_rev_reg_issued(self.request)

    async def test_get_cred_rev_record(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        CRED_REV_ID = "1"

        self.request.query = {
            "rev_reg_id": REV_REG_ID,
            "cred_rev_id": CRED_REV_ID,
        }

        with (
            mock.patch.object(
                test_module.IssuerCredRevRecord,
                "retrieve_by_ids",
                mock.CoroutineMock(),
            ) as mock_retrieve,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_retrieve.return_value = mock.MagicMock(
                serialize=mock.MagicMock(return_value="dummy")
            )
            result = await test_module.get_cred_rev_record(self.request)

            mock_json_response.assert_called_once_with({"result": "dummy"})
            assert result is mock_json_response.return_value

    async def test_get_cred_rev_record_by_cred_ex_id(self):
        CRED_EX_ID = test_module.UUID4_EXAMPLE

        self.request.query = {"cred_ex_id": CRED_EX_ID}

        with (
            mock.patch.object(
                test_module.IssuerCredRevRecord,
                "retrieve_by_cred_ex_id",
                mock.CoroutineMock(),
            ) as mock_retrieve,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_retrieve.return_value = mock.MagicMock(
                serialize=mock.MagicMock(return_value="dummy")
            )
            result = await test_module.get_cred_rev_record(self.request)

            mock_json_response.assert_called_once_with({"result": "dummy"})
            assert result is mock_json_response.return_value

    async def test_get_cred_rev_record_not_found(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        CRED_REV_ID = "1"

        self.request.json = mock.CoroutineMock(
            return_value={
                "rev_reg_id": REV_REG_ID,
                "cred_rev_id": CRED_REV_ID,
            }
        )

        with mock.patch.object(
            test_module.IssuerCredRevRecord,
            "retrieve_by_cred_ex_id",
            mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError("no such rec")
            ),
        ):
            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.get_cred_rev_record(self.request)

    async def test_get_active_rev_reg(self):
        CRED_DEF_ID = f"{self.test_did}:3:CL:1234:default"
        self.request.match_info = {"cred_def_id": CRED_DEF_ID}

        with (
            mock.patch.object(
                test_module, "IndyRevocation", autospec=True
            ) as mock_indy_revoc,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_indy_revoc.return_value = mock.MagicMock(
                get_active_issuer_rev_reg_record=mock.CoroutineMock(
                    return_value=mock.MagicMock(
                        serialize=mock.MagicMock(return_value="dummy")
                    )
                )
            )

            result = await test_module.get_active_rev_reg(self.request)
            mock_json_response.assert_called_once_with({"result": "dummy"})
            assert result is mock_json_response.return_value

    async def test_get_active_rev_reg_not_found(self):
        CRED_DEF_ID = f"{self.test_did}:3:CL:1234:default"
        self.request.match_info = {"cred_def_id": CRED_DEF_ID}

        with (
            mock.patch.object(
                test_module, "IndyRevocation", autospec=True
            ) as mock_indy_revoc,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_indy_revoc.return_value = mock.MagicMock(
                get_active_issuer_rev_reg_record=mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(error_code="dummy")
                )
            )

            with self.assertRaises(HTTPNotFound):
                await test_module.get_active_rev_reg(self.request)
            mock_json_response.assert_not_called()

    async def test_get_tails_file(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with (
            mock.patch.object(
                test_module, "IndyRevocation", autospec=True
            ) as mock_indy_revoc,
            mock.patch.object(
                test_module.web, "FileResponse", mock.Mock()
            ) as mock_file_response,
        ):
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    return_value=mock.MagicMock(tails_local_path="dummy")
                )
            )

            result = await test_module.get_tails_file(self.request)
            mock_file_response.assert_called_once_with(path="dummy", status=200)
            assert result is mock_file_response.return_value

    async def test_get_tails_file_not_found(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with (
            mock.patch.object(
                test_module, "IndyRevocation", autospec=True
            ) as mock_indy_revoc,
            mock.patch.object(
                test_module.web, "FileResponse", mock.Mock()
            ) as mock_file_response,
        ):
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(error_code="dummy")
                )
            )

            with self.assertRaises(HTTPNotFound):
                await test_module.get_tails_file(self.request)
            mock_file_response.assert_not_called()

    async def test_upload_tails_file_basic(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with (
            mock.patch.object(
                test_module, "IndyRevocation", autospec=True
            ) as mock_indy_revoc,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_upload = mock.CoroutineMock()
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    return_value=mock.MagicMock(
                        tails_local_path=f"/tmp/tails/{REV_REG_ID}",
                        has_local_tails_file=True,
                        upload_tails_file=mock_upload,
                    )
                )
            )
            result = await test_module.upload_tails_file(self.request)
            mock_upload.assert_awaited_once()
            mock_json_response.assert_called_once_with({})
            assert result is mock_json_response.return_value

    async def test_upload_tails_file_no_local_tails_file(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc:
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    return_value=mock.MagicMock(
                        tails_local_path=f"/tmp/tails/{REV_REG_ID}",
                        has_local_tails_file=False,
                    )
                )
            )

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.upload_tails_file(self.request)

    async def test_upload_tails_file_fail(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc:
            mock_upload = mock.CoroutineMock(side_effect=RevocationError("test"))
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    return_value=mock.MagicMock(
                        tails_local_path=f"/tmp/tails/{REV_REG_ID}",
                        has_local_tails_file=True,
                        upload_tails_file=mock_upload,
                    )
                )
            )

            with self.assertRaises(test_module.web.HTTPInternalServerError):
                await test_module.upload_tails_file(self.request)

    async def test_send_rev_reg_def(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with (
            mock.patch.object(
                test_module, "IndyRevocation", autospec=True
            ) as mock_indy_revoc,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    return_value=mock.MagicMock(
                        send_def=mock.CoroutineMock(),
                        send_entry=mock.CoroutineMock(),
                        serialize=mock.MagicMock(return_value="dummy"),
                    )
                )
            )

            result = await test_module.send_rev_reg_def(self.request)
            mock_json_response.assert_called_once_with({"sent": "dummy"})
            assert result is mock_json_response.return_value

    async def test_send_rev_reg_def_not_found(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with (
            mock.patch.object(
                test_module, "IndyRevocation", autospec=True
            ) as mock_indy_revoc,
            mock.patch.object(
                test_module.web, "FileResponse", mock.Mock()
            ) as mock_json_response,
        ):
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(error_code="dummy")
                )
            )

            with self.assertRaises(HTTPNotFound):
                await test_module.send_rev_reg_def(self.request)
            mock_json_response.assert_not_called()

    async def test_send_rev_reg_def_x(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc:
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    return_value=mock.MagicMock(
                        send_def=mock.CoroutineMock(
                            side_effect=test_module.RevocationError()
                        ),
                    )
                )
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.send_rev_reg_def(self.request)

    async def test_send_rev_reg_entry(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with (
            mock.patch.object(
                test_module, "IndyRevocation", autospec=True
            ) as mock_indy_revoc,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    return_value=mock.MagicMock(
                        send_entry=mock.CoroutineMock(),
                        serialize=mock.MagicMock(return_value="dummy"),
                    )
                )
            )

            result = await test_module.send_rev_reg_entry(self.request)
            mock_json_response.assert_called_once_with({"result": "dummy"})
            assert result is mock_json_response.return_value

    async def test_send_rev_reg_entry_not_found(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with (
            mock.patch.object(
                test_module, "IndyRevocation", autospec=True
            ) as mock_indy_revoc,
            mock.patch.object(
                test_module.web, "FileResponse", mock.Mock()
            ) as mock_json_response,
        ):
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(error_code="dummy")
                )
            )

            with self.assertRaises(HTTPNotFound):
                await test_module.send_rev_reg_entry(self.request)
            mock_json_response.assert_not_called()

    async def test_send_rev_reg_entry_x(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc:
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    return_value=mock.MagicMock(
                        send_entry=mock.CoroutineMock(
                            side_effect=test_module.RevocationError()
                        ),
                    )
                )
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.send_rev_reg_entry(self.request)

    async def test_update_rev_reg(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}
        self.request.json = mock.CoroutineMock(
            return_value={"tails_public_uri": f"http://sample.ca:8181/tails/{REV_REG_ID}"}
        )

        with (
            mock.patch.object(
                test_module, "IndyRevocation", autospec=True
            ) as mock_indy_revoc,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    return_value=mock.MagicMock(
                        set_tails_file_public_uri=mock.CoroutineMock(),
                        save=mock.CoroutineMock(),
                        serialize=mock.MagicMock(return_value="dummy"),
                    )
                )
            )

            result = await test_module.update_rev_reg(self.request)
            mock_json_response.assert_called_once_with({"result": "dummy"})
            assert result is mock_json_response.return_value

    async def test_update_rev_reg_not_found(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}
        self.request.json = mock.CoroutineMock(
            return_value={"tails_public_uri": f"http://sample.ca:8181/tails/{REV_REG_ID}"}
        )

        with (
            mock.patch.object(
                test_module, "IndyRevocation", autospec=True
            ) as mock_indy_revoc,
            mock.patch.object(
                test_module.web, "FileResponse", mock.Mock()
            ) as mock_json_response,
        ):
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(error_code="dummy")
                )
            )

            with self.assertRaises(HTTPNotFound):
                await test_module.update_rev_reg(self.request)
            mock_json_response.assert_not_called()

    async def test_update_rev_reg_x(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}
        self.request.json = mock.CoroutineMock(
            return_value={"tails_public_uri": f"http://sample.ca:8181/tails/{REV_REG_ID}"}
        )

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc:
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    return_value=mock.MagicMock(
                        set_tails_file_public_uri=mock.CoroutineMock(
                            side_effect=test_module.RevocationError()
                        ),
                    )
                )
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.update_rev_reg(self.request)

    async def test_set_rev_reg_state(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}
        self.request.json = mock.CoroutineMock(
            return_value={
                "max_cred_num": "1000",
            }
        )
        self.request.query = {
            "state": test_module.IssuerRevRegRecord.STATE_ACTIVE,
        }

        with (
            mock.patch.object(
                test_module, "IndyRevocation", autospec=True
            ) as mock_indy_revoc,
            mock.patch.object(
                test_module.web, "json_response", mock.Mock()
            ) as mock_json_response,
        ):
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    return_value=mock.MagicMock(
                        set_state=mock.CoroutineMock(),
                        save=mock.CoroutineMock(),
                        serialize=mock.MagicMock(return_value="dummy"),
                    )
                )
            )

            result = await test_module.set_rev_reg_state(self.request)
            mock_json_response.assert_called_once_with({"result": "dummy"})
            assert result is mock_json_response.return_value

    async def test_set_rev_reg_state_not_found(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}
        self.request.json = mock.CoroutineMock(
            return_value={
                "max_cred_num": "1000",
            }
        )
        self.request.query = {
            "state": test_module.IssuerRevRegRecord.STATE_ACTIVE,
        }

        with (
            mock.patch.object(
                test_module, "IndyRevocation", autospec=True
            ) as mock_indy_revoc,
            mock.patch.object(
                test_module.web, "FileResponse", mock.Mock()
            ) as mock_json_response,
        ):
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(error_code="dummy")
                )
            )

            with self.assertRaises(HTTPNotFound):
                await test_module.set_rev_reg_state(self.request)
            mock_json_response.assert_not_called()

    async def test_register(self):
        mock_app = mock.MagicMock()
        mock_app.add_routes = mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = mock.MagicMock(
            _state={
                "swagger_dict": {
                    "paths": {
                        "/revocation/registry/{rev_reg_id}/tails-file": {
                            "get": {"responses": {"200": {"description": "tails file"}}}
                        }
                    }
                }
            }
        )
        test_module.post_process_routes(mock_app)
        assert mock_app._state["swagger_dict"]["paths"][
            "/revocation/registry/{rev_reg_id}/tails-file"
        ]["get"]["responses"]["200"]["schema"] == {"type": "string", "format": "binary"}

        assert "tags" in mock_app._state["swagger_dict"]

    @mock.patch.object(
        IssuerRevRegRecord, "retrieve_by_revoc_reg_id", return_value=mock.MagicMock()
    )
    @mock.patch.object(
        RevocationManager, "update_rev_reg_revoked_state", return_value=(True, True, True)
    )
    async def test_update_rev_reg_revoked_state(self, *_):
        self.request.query = {"apply_ledger_update": "true"}
        self.request.match_info = {"rev_reg_id": "rev_reg_id"}

        mock_ledger_manager = mock.MagicMock(BaseMultipleLedgerManager, autospec=True)
        mock_ledger_manager.get_write_ledgers = mock.CoroutineMock("ledger")
        self.context.injector.bind_instance(
            BaseMultipleLedgerManager, mock_ledger_manager
        )

        mock_ledger = mock.MagicMock(BaseLedger, autospec=True)
        mock_ledger.pool = mock.MagicMock(genesis_txns="genesis_txns")
        self.context.injector.bind_instance(BaseLedger, mock_ledger)
        self.profile.context.injector.bind_instance(BaseLedger, mock_ledger)

        result = await test_module.update_rev_reg_revoked_state(self.request)
        assert result.status == 200


def make_mock_request(query=None, path="/admin/revocation/delete_tails"):
    query = query or {}
    request = mock.MagicMock()
    request.__getitem__.side_effect = lambda key: {
        "context": mock.MagicMock(profile=mock.MagicMock())
    }[key]
    request.headers = {"Authorization": "Bearer fake-token"}
    request.query = MultiDict(query)
    request.path = path
    return request


@pytest.mark.asyncio
class TestDeleteTails:
    def setup_method(self):
        self.rev_reg_id = "rev_reg_id_123"
        self.cred_def_id = "cred_def_id_456"
        self.main_dir_rev = "path/to/main/dir/rev"
        os.makedirs(self.main_dir_rev, exist_ok=True)
        tails_file = os.path.join(self.main_dir_rev, "tails")
        with open(tails_file, "w") as f:
            f.write("test tails file")

    @mock.patch("acapy_agent.revocation.routes.IndyRevocation.get_issuer_rev_reg_record")
    @mock.patch("acapy_agent.revocation.routes.shutil.rmtree")
    async def test_delete_tails_by_rev_reg_id(self, mock_rmtree, mock_get_rev_reg_record):
        tails_file_path = os.path.join(self.main_dir_rev, "tails")
        mock_record = mock.AsyncMock()
        mock_record.tails_local_path = tails_file_path

        mock_get_rev_reg_record.return_value = mock_record

        request = make_mock_request({"rev_reg_id": self.rev_reg_id})

        result = await test_module.delete_tails(request)

        mock_rmtree.assert_called_once_with(self.main_dir_rev)

        body_bytes = result.body
        body = json.loads(body_bytes.decode("utf-8"))

        assert "message" in body
        assert body["message"] == "All files deleted successfully"

    @mock.patch("acapy_agent.revocation.routes.os.listdir")
    @mock.patch("acapy_agent.revocation.routes.IssuerRevRegRecord.query_by_cred_def_id")
    @mock.patch("acapy_agent.revocation.routes.shutil.rmtree")
    async def test_delete_tails_by_cred_def_id(
        self, mock_rmtree, mock_query_by_cred_def_id, mock_listdir
    ):
        main_dir_cred = "/path/to/main/dir"
        cred_def_id = self.cred_def_id
        cred_dir_name = f"{cred_def_id}_folder"

        mock_listdir.return_value = [cred_dir_name, "other_folder"]

        record = mock.Mock()
        record.tails_local_path = os.path.join(main_dir_cred, cred_dir_name, "tails")
        mock_query_by_cred_def_id.return_value = [record]

        request = make_mock_request({"cred_def_id": cred_def_id})

        result = await test_module.delete_tails(request)

        expected_rmtree_path = os.path.join(main_dir_cred, cred_dir_name)
        mock_rmtree.assert_called_once_with(expected_rmtree_path)

        body_bytes = result.body
        body = json.loads(body_bytes.decode("utf-8"))

        assert "message" in body
        assert body["message"] == "All files deleted successfully"

    @mock.patch("acapy_agent.revocation.routes.IssuerRevRegRecord.query_by_cred_def_id")
    @mock.patch("acapy_agent.revocation.routes.os.listdir")
    async def test_delete_tails_not_found(self, mock_listdir, mock_query_by_cred_def_id):
        mock_query_by_cred_def_id.return_value = []
        mock_listdir.return_value = []  # Important! Avoid list index error.

        request = make_mock_request({"cred_def_id": "nonexistent_cred_def_id"})

        result = await test_module.delete_tails(request)

        if hasattr(result, "json"):
            body = await result.json()
        elif hasattr(result, "body"):
            body = json.loads(result.body.decode())
        else:
            body = result

        assert "message" in body

    def teardown_method(self):
        if os.path.exists(self.main_dir_rev):
            shutil.rmtree(self.main_dir_rev)
