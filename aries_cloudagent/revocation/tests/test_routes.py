import os
import shutil
from unittest import IsolatedAsyncioTestCase

import pytest
from aiohttp.web import HTTPBadRequest, HTTPNotFound

from aries_cloudagent.core.in_memory import InMemoryProfile
from aries_cloudagent.revocation.error import RevocationError
from aries_cloudagent.tests import mock

from ...admin.request_context import AdminRequestContext
from ...askar.profile_anon import AskarAnoncredsProfile
from ...storage.in_memory import InMemoryStorage
from .. import routes as test_module


class TestRevocationRoutes(IsolatedAsyncioTestCase):
    def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.context = self.profile.context
        setattr(self.context, "profile", self.profile)
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

        self.test_did = "sample-did"

        self.author_profile = InMemoryProfile.test_profile()
        self.author_profile.settings.set_value("endorser.author", True)
        self.author_context = self.author_profile.context
        setattr(self.author_context, "profile", self.author_profile)
        self.author_request_dict = {
            "context": self.author_context,
            "outbound_message_router": mock.CoroutineMock(),
        }
        self.author_request = mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.author_request_dict[k],
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
                req.validate_fields(
                    {"cred_rev_id": test_module.INDY_CRED_REV_ID_EXAMPLE}
                )
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

        with mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr, mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
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

        with mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr, mock.patch.object(
            test_module,
            "get_endorser_connection_id",
            mock.CoroutineMock(return_value="dummy-conn-id"),
        ), mock.patch.object(
            test_module.web, "json_response"
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
            }
        )

        with mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr, mock.patch.object(
            test_module.web, "json_response"
        ), mock.patch.object(
            test_module,
            "get_endorser_connection_id",
            mock.CoroutineMock(return_value="test_conn_id"),
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

        with mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr, mock.patch.object(
            test_module,
            "get_endorser_connection_id",
            mock.CoroutineMock(return_value="dummy-conn-id"),
        ), mock.patch.object(
            test_module.web, "json_response"
        ):
            mock_mgr.return_value.revoke_credential = mock.CoroutineMock(
                return_value={"result": "..."}
            )

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

        with mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr, mock.patch.object(
            test_module.web, "json_response"
        ), mock.patch.object(
            test_module,
            "get_endorser_connection_id",
            mock.CoroutineMock(return_value="test_conn_id"),
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

        with mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr, mock.patch.object(
            test_module,
            "get_endorser_connection_id",
            mock.CoroutineMock(return_value=None),
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

        with mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr, mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
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

        with mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr, mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            mock_mgr.return_value.revoke_credential = mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.revoke(self.request)

    async def test_publish_revocations(self):
        self.request.json = mock.CoroutineMock()

        with mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr, mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            pub_pending = mock.CoroutineMock()
            mock_mgr.return_value.publish_pending_revocations = mock.CoroutineMock(
                return_value=({}, pub_pending.return_value)
            )

            await test_module.publish_revocations(self.request)

            mock_response.assert_called_once_with(
                {"rrid2crid": pub_pending.return_value}
            )

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
        self.author_request.json = mock.CoroutineMock()

        with mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr, mock.patch.object(
            test_module,
            "get_endorser_connection_id",
            mock.CoroutineMock(return_value="dummy-conn-id"),
        ), mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            pub_pending = mock.CoroutineMock()
            mock_mgr.return_value.publish_pending_revocations = mock.CoroutineMock(
                return_value=({}, pub_pending.return_value)
            )

            await test_module.publish_revocations(self.author_request)

            mock_response.assert_called_once_with(
                {"rrid2crid": pub_pending.return_value}
            )

    async def test_publish_revocations_endorser_x(self):
        self.author_request.json = mock.CoroutineMock()

        with mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr, mock.patch.object(
            test_module,
            "get_endorser_connection_id",
            mock.CoroutineMock(return_value=None),
        ), mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            pub_pending = mock.CoroutineMock()
            mock_mgr.return_value.publish_pending_revocations = pub_pending
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.publish_revocations(self.author_request)

    async def test_clear_pending_revocations(self):
        self.request.json = mock.CoroutineMock()

        with mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr, mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            clear_pending = mock.CoroutineMock()
            mock_mgr.return_value.clear_pending_revocations = clear_pending

            await test_module.clear_pending_revocations(self.request)

            mock_response.assert_called_once_with(
                {"rrid2crid": clear_pending.return_value}
            )

    async def test_clear_pending_revocations_x(self):
        self.request.json = mock.CoroutineMock()

        with mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr, mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
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

        with mock.patch.object(
            InMemoryStorage, "find_all_records", autospec=True
        ) as mock_find, mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
            mock_find.return_value = True
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

        with mock.patch.object(
            InMemoryStorage, "find_all_records", autospec=True
        ) as mock_find, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
            mock_find.return_value = False

            with self.assertRaises(HTTPNotFound):
                result = await test_module.create_rev_reg(self.request)
            mock_json_response.assert_not_called()

    async def test_create_rev_reg_no_revo_support(self):
        CRED_DEF_ID = f"{self.test_did}:3:CL:1234:default"
        self.request.json = mock.CoroutineMock(
            return_value={
                "max_cred_num": "1000",
                "credential_definition_id": CRED_DEF_ID,
            }
        )

        with mock.patch.object(
            InMemoryStorage, "find_all_records", autospec=True
        ) as mock_find, mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
            mock_find = True
            mock_indy_revoc.return_value = mock.MagicMock(
                init_issuer_registry=mock.CoroutineMock(
                    side_effect=test_module.RevocationNotSupportedError(
                        error_code="dummy"
                    )
                )
            )

            with self.assertRaises(HTTPBadRequest):
                result = await test_module.create_rev_reg(self.request)

            mock_json_response.assert_not_called()

    async def test_rev_regs_created(self):
        CRED_DEF_ID = f"{self.test_did}:3:CL:1234:default"
        self.request.query = {
            "cred_def_id": CRED_DEF_ID,
            "state": test_module.IssuerRevRegRecord.STATE_ACTIVE,
        }

        with mock.patch.object(
            test_module.IssuerRevRegRecord, "query", mock.CoroutineMock()
        ) as mock_query, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
            mock_query.return_value = [mock.MagicMock(revoc_reg_id="dummy")]

            result = await test_module.rev_regs_created(self.request)
            mock_json_response.assert_called_once_with({"rev_reg_ids": ["dummy"]})
            assert result is mock_json_response.return_value

    async def test_get_rev_reg(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
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

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(error_code="dummy")
                )
            )

            with self.assertRaises(HTTPNotFound):
                result = await test_module.get_rev_reg(self.request)
            mock_json_response.assert_not_called()

    async def test_get_rev_reg_issued(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with mock.patch.object(
            test_module.IssuerRevRegRecord,
            "retrieve_by_revoc_reg_id",
            mock.CoroutineMock(),
        ) as mock_retrieve, mock.patch.object(
            test_module.IssuerCredRevRecord,
            "query_by_ids",
            mock.CoroutineMock(),
        ) as mock_query, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
            mock_query.return_value = return_value = [{"...": "..."}, {"...": "..."}]
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

        with mock.patch.object(
            test_module.IssuerCredRevRecord,
            "retrieve_by_ids",
            mock.CoroutineMock(),
        ) as mock_retrieve, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
            mock_retrieve.return_value = mock.MagicMock(
                serialize=mock.MagicMock(return_value="dummy")
            )
            result = await test_module.get_cred_rev_record(self.request)

            mock_json_response.assert_called_once_with({"result": "dummy"})
            assert result is mock_json_response.return_value

    async def test_get_cred_rev_record_by_cred_ex_id(self):
        CRED_EX_ID = test_module.UUID4_EXAMPLE

        self.request.query = {"cred_ex_id": CRED_EX_ID}

        with mock.patch.object(
            test_module.IssuerCredRevRecord,
            "retrieve_by_cred_ex_id",
            mock.CoroutineMock(),
        ) as mock_retrieve, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
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
            "retrieve_by_ids",
            mock.CoroutineMock(),
        ) as mock_retrieve:
            mock_retrieve.side_effect = test_module.StorageNotFoundError("no such rec")
            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.get_cred_rev_record(self.request)

    async def test_get_active_rev_reg(self):
        CRED_DEF_ID = f"{self.test_did}:3:CL:1234:default"
        self.request.match_info = {"cred_def_id": CRED_DEF_ID}

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
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

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = mock.MagicMock(
                get_active_issuer_rev_reg_record=mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(error_code="dummy")
                )
            )

            with self.assertRaises(HTTPNotFound):
                result = await test_module.get_active_rev_reg(self.request)
            mock_json_response.assert_not_called()

    async def test_get_tails_file(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, mock.patch.object(
            test_module.web, "FileResponse", mock.Mock()
        ) as mock_file_response:
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

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, mock.patch.object(
            test_module.web, "FileResponse", mock.Mock()
        ) as mock_file_response:
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(error_code="dummy")
                )
            )

            with self.assertRaises(HTTPNotFound):
                result = await test_module.get_tails_file(self.request)
            mock_file_response.assert_not_called()

    async def test_upload_tails_file_basic(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
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

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
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

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, mock.patch.object(
            test_module.web, "FileResponse", mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(error_code="dummy")
                )
            )

            with self.assertRaises(HTTPNotFound):
                result = await test_module.send_rev_reg_def(self.request)
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

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
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

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, mock.patch.object(
            test_module.web, "FileResponse", mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(error_code="dummy")
                )
            )

            with self.assertRaises(HTTPNotFound):
                result = await test_module.send_rev_reg_entry(self.request)
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
            return_value={
                "tails_public_uri": f"http://sample.ca:8181/tails/{REV_REG_ID}"
            }
        )

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
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
            return_value={
                "tails_public_uri": f"http://sample.ca:8181/tails/{REV_REG_ID}"
            }
        )

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, mock.patch.object(
            test_module.web, "FileResponse", mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(error_code="dummy")
                )
            )

            with self.assertRaises(HTTPNotFound):
                result = await test_module.update_rev_reg(self.request)
            mock_json_response.assert_not_called()

    async def test_update_rev_reg_x(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}
        self.request.json = mock.CoroutineMock(
            return_value={
                "tails_public_uri": f"http://sample.ca:8181/tails/{REV_REG_ID}"
            }
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

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
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

        with mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, mock.patch.object(
            test_module.web, "FileResponse", mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = mock.MagicMock(
                get_issuer_rev_reg_record=mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(error_code="dummy")
                )
            )

            with self.assertRaises(HTTPNotFound):
                result = await test_module.set_rev_reg_state(self.request)
            mock_json_response.assert_not_called()

    async def test_wrong_profile_403(self):
        self.profile = InMemoryProfile.test_profile(
            settings={"wallet.type": "askar"},
            profile_class=AskarAnoncredsProfile,
        )
        self.context = AdminRequestContext.test_context({}, self.profile)
        self.request_dict = {
            "context": self.context,
        }
        self.request = mock.MagicMock(
            app={},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
            context=self.context,
        )

        self.request.json = mock.CoroutineMock(
            return_value={
                "rev_reg_id": "rr_id",
                "cred_rev_id": "23",
                "publish": "false",
            }
        )
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.revoke(self.request)

        self.request.json = mock.CoroutineMock()
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.publish_revocations(self.request)

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.clear_pending_revocations(self.request)

        CRED_DEF_ID = f"{self.test_did}:3:CL:1234:default"
        self.request.json = mock.CoroutineMock(
            return_value={
                "max_cred_num": "1000",
                "credential_definition_id": CRED_DEF_ID,
            }
        )
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.create_rev_reg(self.request)

        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.get_rev_reg(self.request)
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.get_rev_reg_issued(self.request)

        CRED_REV_ID = "1"
        self.request.query = {
            "rev_reg_id": REV_REG_ID,
            "cred_rev_id": CRED_REV_ID,
        }
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.get_cred_rev_record(self.request)

        self.request.match_info = {"cred_def_id": CRED_DEF_ID}
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.get_active_rev_reg(self.request)

        self.request.match_info = {"rev_reg_id": REV_REG_ID}
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.get_tails_file(self.request)
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.upload_tails_file(self.request)
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.send_rev_reg_def(self.request)
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.send_rev_reg_entry(self.request)
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.update_rev_reg(self.request)
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.set_rev_reg_state(self.request)

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


class TestDeleteTails(IsolatedAsyncioTestCase):
    def setUp(self):
        self.rev_reg_id = "rev_reg_id_123"
        self.cred_def_id = "cred_def_id_456"

        self.main_dir_rev = "path/to/main/dir/rev"
        self.tails_path = os.path.join(self.main_dir_rev, "tails")
        if not (os.path.exists(self.main_dir_rev)):
            os.makedirs(self.main_dir_rev)
        open(self.tails_path, "w").close()

    @pytest.mark.xfail(reason="This test never worked but was skipped due to a bug")
    async def test_delete_tails_by_rev_reg_id(self):
        # Setup
        rev_reg_id = self.rev_reg_id

        # Test
        result = await test_module.delete_tails(
            {"context": None, "query": {"rev_reg_id": rev_reg_id}}
        )

        # Assert
        self.assertEqual(result, {"message": "All files deleted successfully"})
        self.assertFalse(os.path.exists(self.tails_path))

    @pytest.mark.xfail(reason="This test never worked but was skipped due to a bug")
    async def test_delete_tails_by_cred_def_id(self):
        # Setup
        cred_def_id = self.cred_def_id
        main_dir_cred = "path/to/main/dir/cred"
        os.makedirs(main_dir_cred)
        cred_dir = os.path.join(main_dir_cred, cred_def_id)
        os.makedirs(cred_dir)

        # Test
        result = await test_module.delete_tails(
            {"context": None, "query": {"cred_def_id": cred_def_id}}
        )

        # Assert
        self.assertEqual(result, {"message": "All files deleted successfully"})
        self.assertFalse(os.path.exists(cred_dir))
        self.assertTrue(os.path.exists(main_dir_cred))

    @pytest.mark.xfail(reason="This test never worked but was skipped due to a bug")
    async def test_delete_tails_not_found(self):
        # Setup
        cred_def_id = "invalid_cred_def_id"

        # Test
        result = await test_module.delete_tails(
            {"context": None, "query": {"cred_def_id": cred_def_id}}
        )

        # Assert
        self.assertEqual(result, {"message": "No such file or directory"})
        self.assertTrue(os.path.exists(self.main_dir_rev))

    def tearDown(self):
        if os.path.exists(self.main_dir_rev):
            shutil.rmtree(self.main_dir_rev)
