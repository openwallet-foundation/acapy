import os
import shutil
from unittest import IsolatedAsyncioTestCase

import pytest
from aiohttp.web import HTTPNotFound

from aries_cloudagent.tests import mock

from ...admin.request_context import AdminRequestContext
from ...anoncreds.models.anoncreds_revocation import (
    RevRegDef,
    RevRegDefValue,
)
from ...askar.profile import AskarProfile
from ...askar.profile_anon import AskarAnoncredsProfile
from ...core.in_memory import InMemoryProfile
from .. import routes as test_module


class TestRevocationRoutes(IsolatedAsyncioTestCase):
    def setUp(self):
        self.profile = InMemoryProfile.test_profile(profile_class=AskarAnoncredsProfile)
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

    async def test_validate_cred_rev_rec_qs_and_revoke_req(self):
        for req in (
            test_module.CredRevRecordQueryStringSchema(),
            test_module.RevokeRequestSchemaAnoncreds(),
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
            mock_mgr.return_value.publish_pending_revocations = pub_pending

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

    async def test_rev_regs_created(self):
        CRED_DEF_ID = f"{self.test_did}:3:CL:1234:default"
        self.request.query = {
            "cred_def_id": CRED_DEF_ID,
            "state": test_module.IssuerRevRegRecord.STATE_ACTIVE,
        }

        with mock.patch.object(
            test_module.AnonCredsRevocation,
            "get_created_revocation_registry_definitions",
            mock.AsyncMock(),
        ) as mock_query, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
            mock_query.return_value = ["dummy"]

            result = await test_module.get_rev_regs(self.request)
            mock_json_response.assert_called_once_with({"rev_reg_ids": ["dummy"]})
            assert result is mock_json_response.return_value

    async def test_get_rev_reg(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        RECORD_ID = "4ba81d6e-f341-4e37-83d4-6b1d3e25a7bd"
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with mock.patch.object(
            test_module, "AnonCredsRevocation", autospec=True
        ) as mock_anon_creds_revoc, mock.patch.object(
            test_module.uuid, "uuid4", mock.Mock()
        ) as mock_uuid, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
            mock_uuid.return_value = RECORD_ID
            mock_anon_creds_revoc.return_value = mock.MagicMock(
                get_created_revocation_registry_definition=mock.AsyncMock(
                    return_value=RevRegDef(
                        issuer_id="issuer_id",
                        type="CL_ACCUM",
                        cred_def_id="cred_def_id",
                        tag="tag",
                        value=RevRegDefValue(
                            public_keys={},
                            max_cred_num=100,
                            tails_hash="tails_hash",
                            tails_location="tails_location",
                        ),
                    )
                ),
                get_created_revocation_registry_definition_state=mock.AsyncMock(
                    return_value=test_module.RevRegDefState.STATE_FINISHED
                ),
                get_pending_revocations=mock.AsyncMock(return_value=[]),
            )

            result = await test_module.get_rev_reg(self.request)
            mock_json_response.assert_called_once_with(
                {
                    "result": {
                        "tails_local_path": "tails_location",
                        "tails_hash": "tails_hash",
                        "state": test_module.RevRegDefState.STATE_FINISHED,
                        "issuer_did": "issuer_id",
                        "pending_pub": [],
                        "revoc_reg_def": {
                            "ver": "1.0",
                            "id": REV_REG_ID,
                            "revocDefType": "CL_ACCUM",
                            "tag": "tag",
                            "credDefId": "cred_def_id",
                        },
                        "max_cred_num": 100,
                        "record_id": RECORD_ID,
                        "tag": "tag",
                        "revoc_def_type": "CL_ACCUM",
                        "revoc_reg_id": REV_REG_ID,
                        "cred_def_id": "cred_def_id",
                    }
                }
            )
            assert result is mock_json_response.return_value

    async def test_get_rev_reg_not_found(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with mock.patch.object(
            test_module, "AnonCredsRevocation", autospec=True
        ) as mock_anon_creds_revoc, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
            mock_anon_creds_revoc.return_value = mock.MagicMock(
                get_created_revocation_registry_definition=mock.AsyncMock(
                    return_value=None
                ),
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
            test_module.AnonCredsRevocation,
            "get_created_revocation_registry_definition",
            autospec=True,
        ) as mock_rev_reg_def, mock.patch.object(
            test_module.IssuerCredRevRecord,
            "query_by_ids",
            mock.CoroutineMock(),
        ) as mock_query, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
            mock_rev_reg_def.return_value = {}
            mock_query.return_value = return_value = [{}, {}]
            result = await test_module.get_rev_reg_issued_count(self.request)

            mock_json_response.assert_called_once_with({"result": 2})
            assert result is mock_json_response.return_value

    async def test_get_rev_reg_issued_x(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with mock.patch.object(
            test_module.AnonCredsRevocation,
            "get_created_revocation_registry_definition",
            autospec=True,
        ) as mock_rev_reg_def:
            mock_rev_reg_def.return_value = None

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

    async def test_get_tails_file(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with mock.patch.object(
            test_module.AnonCredsRevocation,
            "get_created_revocation_registry_definition",
            mock.AsyncMock(),
        ) as mock_get_rev_reg, mock.patch.object(
            test_module.web, "FileResponse", mock.Mock()
        ) as mock_file_response:
            mock_get_rev_reg.return_value = RevRegDef(
                issuer_id="issuer_id",
                type="CL_ACCUM",
                cred_def_id="cred_def_id",
                tag="tag",
                value=RevRegDefValue(
                    public_keys={},
                    max_cred_num=100,
                    tails_hash="tails_hash",
                    tails_location="tails_location",
                ),
            )

            result = await test_module.get_tails_file(self.request)
            mock_file_response.assert_called_once_with(
                path="tails_location", status=200
            )
            assert result is mock_file_response.return_value

    async def test_get_tails_file_not_found(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with mock.patch.object(
            test_module.AnonCredsRevocation,
            "get_created_revocation_registry_definition",
            mock.AsyncMock(),
        ) as mock_get_rev_reg, mock.patch.object(
            test_module.web, "FileResponse", mock.Mock()
        ) as mock_file_response:
            mock_get_rev_reg.return_value = None

            with self.assertRaises(HTTPNotFound):
                result = await test_module.get_tails_file(self.request)
            mock_file_response.assert_not_called()

    async def test_set_rev_reg_state(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        RECORD_ID = "4ba81d6e-f341-4e37-83d4-6b1d3e25a7bd"
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        self.request.query = {
            "state": test_module.RevRegDefState.STATE_FINISHED,
        }

        with mock.patch.object(
            test_module, "AnonCredsRevocation", autospec=True
        ) as mock_anon_creds_revoc, mock.patch.object(
            test_module.uuid, "uuid4", mock.Mock()
        ) as mock_uuid, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
            mock_uuid.return_value = RECORD_ID
            mock_anon_creds_revoc.return_value = mock.MagicMock(
                set_rev_reg_state=mock.AsyncMock(return_value={}),
                get_created_revocation_registry_definition=mock.AsyncMock(
                    return_value=RevRegDef(
                        issuer_id="issuer_id",
                        type="CL_ACCUM",
                        cred_def_id="cred_def_id",
                        tag="tag",
                        value=RevRegDefValue(
                            public_keys={},
                            max_cred_num=100,
                            tails_hash="tails_hash",
                            tails_location="tails_location",
                        ),
                    )
                ),
                get_created_revocation_registry_definition_state=mock.AsyncMock(
                    return_value=test_module.RevRegDefState.STATE_FINISHED
                ),
                get_pending_revocations=mock.AsyncMock(return_value=[]),
            )

            result = await test_module.set_rev_reg_state(self.request)
            mock_json_response.assert_called_once_with(
                {
                    "result": {
                        "tails_local_path": "tails_location",
                        "tails_hash": "tails_hash",
                        "state": test_module.RevRegDefState.STATE_FINISHED,
                        "issuer_did": "issuer_id",
                        "pending_pub": [],
                        "revoc_reg_def": {
                            "ver": "1.0",
                            "id": REV_REG_ID,
                            "revocDefType": "CL_ACCUM",
                            "tag": "tag",
                            "credDefId": "cred_def_id",
                        },
                        "max_cred_num": 100,
                        "record_id": RECORD_ID,
                        "tag": "tag",
                        "revoc_def_type": "CL_ACCUM",
                        "revoc_reg_id": REV_REG_ID,
                        "cred_def_id": "cred_def_id",
                    }
                }
            )
            assert result is mock_json_response.return_value

    async def test_set_rev_reg_state_not_found(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        self.request.query = {
            "state": test_module.RevRegDefState.STATE_FINISHED,
        }

        with mock.patch.object(
            test_module.AnonCredsRevocation,
            "get_created_revocation_registry_definition",
            mock.AsyncMock(),
        ) as mock_rev_reg_def, mock.patch.object(
            test_module.web, "json_response", mock.Mock()
        ) as mock_json_response:
            mock_rev_reg_def.return_value = None

            with self.assertRaises(HTTPNotFound):
                result = await test_module.set_rev_reg_state(self.request)
            mock_json_response.assert_not_called()

    async def test_wrong_profile_403(self):
        self.profile = InMemoryProfile.test_profile(
            settings={"wallet.type": "askar"},
            profile_class=AskarProfile,
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

        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.get_rev_reg(self.request)

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.get_rev_reg_issued_count(self.request)

        CRED_REV_ID = "1"
        self.request.query = {
            "rev_reg_id": REV_REG_ID,
            "cred_rev_id": CRED_REV_ID,
        }
        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.get_cred_rev_record(self.request)

        self.request.match_info = {"rev_reg_id": REV_REG_ID}
        with self.assertRaises(test_module.web.HTTPForbidden):
            result = await test_module.get_tails_file(self.request)

        self.request.query = {
            "state": test_module.RevRegDefState.STATE_FINISHED,
        }
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
