from aiohttp.web import HTTPBadRequest, HTTPNotFound
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ...admin.request_context import AdminRequestContext
from ...storage.in_memory import InMemoryStorage
from ...tails.base import BaseTailsServer

from .. import routes as test_module


class TestRevocationRoutes(AsyncTestCase):
    def setUp(self):
        TailsServer = async_mock.MagicMock(BaseTailsServer, autospec=True)
        self.tails_server = TailsServer()
        self.tails_server.upload_tails_file = async_mock.CoroutineMock(
            return_value=(True, None)
        )
        self.session_inject = {}
        self.context = AdminRequestContext.test_context(self.session_inject)
        self.context.injector.bind_instance(BaseTailsServer, self.tails_server)
        self.request_dict = {"context": self.context}
        self.request = async_mock.MagicMock(
            app={"outbound_message_router": async_mock.CoroutineMock()},
            match_info={},
            query={},
            __getitem__=lambda _, k: self.request_dict[k],
        )

        self.test_did = "sample-did"

    async def test_validate_cred_rev_rec_qs_and_revoke_req(self):
        for req in (
            test_module.CredRevRecordQueryStringSchema(),
            test_module.RevokeRequestSchema(),
        ):
            req.validate_fields(
                {
                    "rev_reg_id": test_module.INDY_REV_REG_ID["example"],
                    "cred_rev_id": test_module.INDY_CRED_REV_ID["example"],
                }
            )
            req.validate_fields({"cred_ex_id": test_module.UUID4["example"]})
            with self.assertRaises(test_module.ValidationError):
                req.validate_fields({})
            with self.assertRaises(test_module.ValidationError):
                req.validate_fields(
                    {"rev_reg_id": test_module.INDY_REV_REG_ID["example"]}
                )
            with self.assertRaises(test_module.ValidationError):
                req.validate_fields(
                    {"cred_rev_id": test_module.INDY_CRED_REV_ID["example"]}
                )
            with self.assertRaises(test_module.ValidationError):
                req.validate_fields(
                    {
                        "rev_reg_id": test_module.INDY_REV_REG_ID["example"],
                        "cred_ex_id": test_module.UUID4["example"],
                    }
                )
            with self.assertRaises(test_module.ValidationError):
                req.validate_fields(
                    {
                        "cred_rev_id": test_module.INDY_CRED_REV_ID["example"],
                        "cred_ex_id": test_module.UUID4["example"],
                    }
                )
            with self.assertRaises(test_module.ValidationError):
                req.validate_fields(
                    {
                        "rev_reg_id": test_module.INDY_REV_REG_ID["example"],
                        "cred_rev_id": test_module.INDY_CRED_REV_ID["example"],
                        "cred_ex_id": test_module.UUID4["example"],
                    }
                )

    async def test_revoke(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "rev_reg_id": "rr_id",
                "cred_rev_id": "23",
                "publish": "false",
            }
        )

        with async_mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_mgr.return_value.revoke_credential = async_mock.CoroutineMock()

            await test_module.revoke(self.request)

            mock_response.assert_called_once_with({})

    async def test_revoke_by_cred_ex_id(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "cred_ex_id": "dummy-cxid",
                "publish": "false",
            }
        )

        with async_mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_mgr.return_value.revoke_credential = async_mock.CoroutineMock()

            await test_module.revoke(self.request)

            mock_response.assert_called_once_with({})

    async def test_revoke_not_found(self):
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "rev_reg_id": "rr_id",
                "cred_rev_id": "23",
                "publish": "false",
            }
        )

        with async_mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:

            mock_mgr.return_value.revoke_credential = async_mock.CoroutineMock(
                side_effect=test_module.StorageNotFoundError()
            )

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.revoke(self.request)

    async def test_publish_revocations(self):
        self.request.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            pub_pending = async_mock.CoroutineMock()
            mock_mgr.return_value.publish_pending_revocations = pub_pending

            await test_module.publish_revocations(self.request)

            mock_response.assert_called_once_with(
                {"rrid2crid": pub_pending.return_value}
            )

    async def test_publish_revocations_x(self):
        self.request.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr:
            pub_pending = async_mock.CoroutineMock(
                side_effect=test_module.RevocationError()
            )
            mock_mgr.return_value.publish_pending_revocations = pub_pending

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.publish_revocations(self.request)

    async def test_clear_pending_revocations(self):
        self.request.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            clear_pending = async_mock.CoroutineMock()
            mock_mgr.return_value.clear_pending_revocations = clear_pending

            await test_module.clear_pending_revocations(self.request)

            mock_response.assert_called_once_with(
                {"rrid2crid": clear_pending.return_value}
            )

    async def test_clear_pending_revocations_x(self):
        self.request.json = async_mock.CoroutineMock()

        with async_mock.patch.object(
            test_module, "RevocationManager", autospec=True
        ) as mock_mgr, async_mock.patch.object(
            test_module.web, "json_response"
        ) as mock_response:
            clear_pending = async_mock.CoroutineMock(
                side_effect=test_module.StorageError()
            )
            mock_mgr.return_value.clear_pending_revocations = clear_pending

            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.clear_pending_revocations(self.request)

    async def test_create_rev_reg(self):
        CRED_DEF_ID = f"{self.test_did}:3:CL:1234:default"
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "max_cred_num": "1000",
                "credential_definition_id": CRED_DEF_ID,
            }
        )

        with async_mock.patch.object(
            InMemoryStorage, "search_records", autospec=True
        ) as mock_search, async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_search.return_value.fetch_all = async_mock.CoroutineMock(
                return_value=True
            )
            mock_indy_revoc.return_value = async_mock.MagicMock(
                init_issuer_registry=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        generate_registry=async_mock.CoroutineMock(),
                        serialize=async_mock.MagicMock(return_value="dummy"),
                    )
                )
            )

            result = await test_module.create_rev_reg(self.request)
            mock_json_response.assert_called_once_with({"result": "dummy"})
            assert result is mock_json_response.return_value

    async def test_create_rev_reg_no_such_cred_def(self):
        CRED_DEF_ID = f"{self.test_did}:3:CL:1234:default"
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "max_cred_num": "1000",
                "credential_definition_id": CRED_DEF_ID,
            }
        )

        with async_mock.patch.object(
            InMemoryStorage, "search_records", autospec=True
        ) as mock_search, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_search.return_value.fetch_all = async_mock.CoroutineMock(
                return_value=False
            )

            with self.assertRaises(HTTPNotFound):
                result = await test_module.create_rev_reg(self.request)
            mock_json_response.assert_not_called()

    async def test_create_rev_reg_no_revo_support(self):
        CRED_DEF_ID = f"{self.test_did}:3:CL:1234:default"
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "max_cred_num": "1000",
                "credential_definition_id": CRED_DEF_ID,
            }
        )

        with async_mock.patch.object(
            InMemoryStorage, "search_records", autospec=True
        ) as mock_search, async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_search.return_value.fetch_all = async_mock.CoroutineMock(
                return_value=True
            )
            mock_indy_revoc.return_value = async_mock.MagicMock(
                init_issuer_registry=async_mock.CoroutineMock(
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
        STATE = "active"
        self.request.query = {
            "cred_def_id": CRED_DEF_ID,
            "state": test_module.IssuerRevRegRecord.STATE_ACTIVE,
        }

        with async_mock.patch.object(
            test_module.IssuerRevRegRecord, "query", async_mock.CoroutineMock()
        ) as mock_query, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_query.return_value = [async_mock.MagicMock(revoc_reg_id="dummy")]

            result = await test_module.rev_regs_created(self.request)
            mock_json_response.assert_called_once_with({"rev_reg_ids": ["dummy"]})
            assert result is mock_json_response.return_value

    async def test_get_rev_reg(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_rev_reg_record=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        serialize=async_mock.MagicMock(return_value="dummy")
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

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_rev_reg_record=async_mock.CoroutineMock(
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

        with async_mock.patch.object(
            test_module.IssuerRevRegRecord,
            "retrieve_by_revoc_reg_id",
            async_mock.CoroutineMock(),
        ) as mock_retrieve, async_mock.patch.object(
            test_module.IssuerCredRevRecord,
            "query_by_ids",
            async_mock.CoroutineMock(),
        ) as mock_query, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_query.return_value = return_value = [{"...": "..."}, {"...": "..."}]
            result = await test_module.get_rev_reg_issued(self.request)

            mock_json_response.assert_called_once_with({"result": 2})
            assert result is mock_json_response.return_value

    async def test_get_rev_reg_issued_x(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with async_mock.patch.object(
            test_module.IssuerRevRegRecord,
            "retrieve_by_revoc_reg_id",
            async_mock.CoroutineMock(),
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

        with async_mock.patch.object(
            test_module.IssuerCredRevRecord,
            "retrieve_by_ids",
            async_mock.CoroutineMock(),
        ) as mock_retrieve, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_retrieve.return_value = async_mock.MagicMock(
                serialize=async_mock.MagicMock(return_value="dummy")
            )
            result = await test_module.get_cred_rev_record(self.request)

            mock_json_response.assert_called_once_with({"result": "dummy"})
            assert result is mock_json_response.return_value

    async def test_get_cred_rev_record_by_cred_ex_id(self):
        CRED_EX_ID = test_module.UUID4["example"]

        self.request.query = {"cred_ex_id": CRED_EX_ID}

        with async_mock.patch.object(
            test_module.IssuerCredRevRecord,
            "retrieve_by_cred_ex_id",
            async_mock.CoroutineMock(),
        ) as mock_retrieve, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_retrieve.return_value = async_mock.MagicMock(
                serialize=async_mock.MagicMock(return_value="dummy")
            )
            result = await test_module.get_cred_rev_record(self.request)

            mock_json_response.assert_called_once_with({"result": "dummy"})
            assert result is mock_json_response.return_value

    async def test_get_cred_rev_record_not_found(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        CRED_REV_ID = "1"

        self.request.json = async_mock.CoroutineMock(
            return_value={
                "rev_reg_id": REV_REG_ID,
                "cred_rev_id": CRED_REV_ID,
            }
        )

        with async_mock.patch.object(
            test_module.IssuerCredRevRecord,
            "retrieve_by_ids",
            async_mock.CoroutineMock(),
        ) as mock_retrieve:
            mock_retrieve.side_effect = test_module.StorageNotFoundError("no such rec")
            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.get_cred_rev_record(self.request)

    async def test_get_active_rev_reg(self):
        CRED_DEF_ID = f"{self.test_did}:3:CL:1234:default"
        self.request.match_info = {"cred_def_id": CRED_DEF_ID}

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_active_issuer_rev_reg_record=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        serialize=async_mock.MagicMock(return_value="dummy")
                    )
                )
            )

            result = await test_module.get_active_rev_reg(self.request)
            mock_json_response.assert_called_once_with({"result": "dummy"})
            assert result is mock_json_response.return_value

    async def test_get_active_rev_reg_not_found(self):
        CRED_DEF_ID = f"{self.test_did}:3:CL:1234:default"
        self.request.match_info = {"cred_def_id": CRED_DEF_ID}

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_active_issuer_rev_reg_record=async_mock.CoroutineMock(
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

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, async_mock.patch.object(
            test_module.web, "FileResponse", async_mock.Mock()
        ) as mock_file_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_rev_reg_record=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(tails_local_path="dummy")
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

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, async_mock.patch.object(
            test_module.web, "FileResponse", async_mock.Mock()
        ) as mock_file_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_rev_reg_record=async_mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(error_code="dummy")
                )
            )

            with self.assertRaises(HTTPNotFound):
                result = await test_module.get_tails_file(self.request)
            mock_file_response.assert_not_called()

    async def test_upload_tails_file(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with async_mock.patch.object(
            test_module, "tails_path", async_mock.MagicMock()
        ) as mock_tails_path, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_tails_path.return_value = f"/tmp/tails/{REV_REG_ID}"

            result = await test_module.upload_tails_file(self.request)
            mock_json_response.assert_called_once_with()
            assert result is mock_json_response.return_value

    async def test_upload_tails_file_no_tails_server(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        self.context.injector.clear_binding(BaseTailsServer)

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.upload_tails_file(self.request)

    async def test_upload_tails_file_no_local_tails_file(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with async_mock.patch.object(
            test_module, "tails_path", async_mock.MagicMock()
        ) as mock_tails_path:
            mock_tails_path.return_value = None

            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.upload_tails_file(self.request)

    async def test_upload_tails_file_fail(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        TailsServer = async_mock.MagicMock(BaseTailsServer, autospec=True)
        self.tails_server = TailsServer()
        self.tails_server.upload_tails_file = async_mock.CoroutineMock(
            return_value=(False, "Internal Server Error")
        )
        self.context.injector.clear_binding(BaseTailsServer)
        self.context.injector.bind_instance(BaseTailsServer, self.tails_server)

        with async_mock.patch.object(
            test_module, "tails_path", async_mock.MagicMock()
        ) as mock_tails_path:
            with self.assertRaises(test_module.web.HTTPInternalServerError):
                await test_module.upload_tails_file(self.request)

    async def test_send_rev_reg_def(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_rev_reg_record=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        send_def=async_mock.CoroutineMock(),
                        send_entry=async_mock.CoroutineMock(),
                        serialize=async_mock.MagicMock(return_value="dummy"),
                    )
                )
            )

            result = await test_module.send_rev_reg_def(self.request)
            mock_json_response.assert_called_once_with({"result": "dummy"})
            assert result is mock_json_response.return_value

    async def test_send_rev_reg_def_not_found(self):
        REV_REG_ID = "{}:4:{}:3:CL:1234:default:CL_ACCUM:default".format(
            self.test_did, self.test_did
        )
        self.request.match_info = {"rev_reg_id": REV_REG_ID}

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, async_mock.patch.object(
            test_module.web, "FileResponse", async_mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_rev_reg_record=async_mock.CoroutineMock(
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

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_rev_reg_record=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        send_def=async_mock.CoroutineMock(
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

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_rev_reg_record=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        send_entry=async_mock.CoroutineMock(),
                        serialize=async_mock.MagicMock(return_value="dummy"),
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

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, async_mock.patch.object(
            test_module.web, "FileResponse", async_mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_rev_reg_record=async_mock.CoroutineMock(
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

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_rev_reg_record=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        send_entry=async_mock.CoroutineMock(
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
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "tails_public_uri": f"http://sample.ca:8181/tails/{REV_REG_ID}"
            }
        )

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_rev_reg_record=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        set_tails_file_public_uri=async_mock.CoroutineMock(),
                        save=async_mock.CoroutineMock(),
                        serialize=async_mock.MagicMock(return_value="dummy"),
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
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "tails_public_uri": f"http://sample.ca:8181/tails/{REV_REG_ID}"
            }
        )

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, async_mock.patch.object(
            test_module.web, "FileResponse", async_mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_rev_reg_record=async_mock.CoroutineMock(
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
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "tails_public_uri": f"http://sample.ca:8181/tails/{REV_REG_ID}"
            }
        )

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_rev_reg_record=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        set_tails_file_public_uri=async_mock.CoroutineMock(
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
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "max_cred_num": "1000",
            }
        )
        self.request.query = {
            "state": test_module.IssuerRevRegRecord.STATE_ACTIVE,
        }

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_rev_reg_record=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        set_state=async_mock.CoroutineMock(),
                        save=async_mock.CoroutineMock(),
                        serialize=async_mock.MagicMock(return_value="dummy"),
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
        self.request.json = async_mock.CoroutineMock(
            return_value={
                "max_cred_num": "1000",
            }
        )
        self.request.query = {
            "state": test_module.IssuerRevRegRecord.STATE_ACTIVE,
        }

        with async_mock.patch.object(
            test_module, "IndyRevocation", autospec=True
        ) as mock_indy_revoc, async_mock.patch.object(
            test_module.web, "FileResponse", async_mock.Mock()
        ) as mock_json_response:
            mock_indy_revoc.return_value = async_mock.MagicMock(
                get_issuer_rev_reg_record=async_mock.CoroutineMock(
                    side_effect=test_module.StorageNotFoundError(error_code="dummy")
                )
            )

            with self.assertRaises(HTTPNotFound):
                result = await test_module.set_rev_reg_state(self.request)
            mock_json_response.assert_not_called()

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(
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
