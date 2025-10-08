from unittest import IsolatedAsyncioTestCase

import pytest
from aiohttp import web
from aiohttp.web import HTTPForbidden, HTTPNotFound
from marshmallow import ValidationError

from ......admin.request_context import AdminRequestContext
from ......storage.error import StorageNotFoundError
from ......tests import mock
from ......utils.testing import create_test_profile
from .....models.issuer_cred_rev_record import IssuerCredRevRecord
from ....common.testing import BaseAnonCredsRouteTestCaseWithOutbound
from .. import routes as test_module
from ..routes import (
    CredRevRecordQueryStringSchema,
    RevokeRequestSchemaAnonCreds,
    get_cred_rev_record,
    revoke,
)


@pytest.mark.anoncreds
class TestAnonCredsCredentialRevocationRoutes(
    BaseAnonCredsRouteTestCaseWithOutbound, IsolatedAsyncioTestCase
):
    async def asyncSetUp(self):
        await super().asyncSetUp()

    def test_validate_cred_rev_rec_qs_and_revoke_req(self):
        for req in (
            CredRevRecordQueryStringSchema(),
            RevokeRequestSchemaAnonCreds(),
        ):
            req.validate_fields(
                {
                    "rev_reg_id": (
                        "did:indy:sovrin:staging:DyZewQF7GvBJ7g8Fg4bQJn:4:did:indy:sovrin:staging:"
                        "DyZewQF7GvBJ7g8Fg4bQJn:3:CL:1234:default:CL_ACCUM:default"
                    ),
                    "cred_rev_id": "1",
                }
            )
            req.validate_fields({"cred_ex_id": "12345678-1234-5678-9abc-def012345678"})
            with self.assertRaises(ValidationError):
                req.validate_fields({})
            with self.assertRaises(ValidationError):
                req.validate_fields(
                    {
                        "rev_reg_id": (
                            "did:indy:sovrin:staging:DyZewQF7GvBJ7g8Fg4bQJn:4:did:indy:sovrin:staging:"
                            "DyZewQF7GvBJ7g8Fg4bQJn:3:CL:1234:default:CL_ACCUM:default"
                        )
                    }
                )
            with self.assertRaises(ValidationError):
                req.validate_fields({"cred_rev_id": "1"})
            with self.assertRaises(ValidationError):
                req.validate_fields(
                    {
                        "rev_reg_id": (
                            "did:indy:sovrin:staging:DyZewQF7GvBJ7g8Fg4bQJn:4:did:indy:sovrin:staging:"
                            "DyZewQF7GvBJ7g8Fg4bQJn:3:CL:1234:default:CL_ACCUM:default"
                        ),
                        "cred_ex_id": "12345678-1234-5678-9abc-def012345678",
                    }
                )
            with self.assertRaises(ValidationError):
                req.validate_fields(
                    {
                        "cred_rev_id": "1",
                        "cred_ex_id": "12345678-1234-5678-9abc-def012345678",
                    }
                )
            with self.assertRaises(ValidationError):
                req.validate_fields(
                    {
                        "rev_reg_id": (
                            "did:indy:sovrin:staging:DyZewQF7GvBJ7g8Fg4bQJn:4:did:indy:sovrin:staging:"
                            "DyZewQF7GvBJ7g8Fg4bQJn:3:CL:1234:default:CL_ACCUM:default"
                        ),
                        "cred_rev_id": "1",
                        "cred_ex_id": "12345678-1234-5678-9abc-def012345678",
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
            mock_mgr.return_value.publish_pending_revocations = pub_pending

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

    async def test_get_cred_rev_record(self):
        self.request.query = {
            "rev_reg_id": "test_rev_reg_id",
            "cred_rev_id": "1",
        }

        with (
            mock.patch.object(
                IssuerCredRevRecord,
                "retrieve_by_ids",
                mock.CoroutineMock(),
            ) as mock_retrieve,
            mock.patch.object(web, "json_response", mock.Mock()) as mock_json_response,
        ):
            mock_retrieve.return_value = [
                mock.MagicMock(serialize=mock.MagicMock(return_value="dummy"))
            ]
            result = await get_cred_rev_record(self.request)

            mock_json_response.assert_called_once_with({"result": "dummy"})
            assert result is mock_json_response.return_value

    async def test_get_cred_rev_record_by_cred_ex_id(self):
        self.request.query = {"cred_ex_id": "12345678-1234-5678-9abc-def012345678"}

        with (
            mock.patch.object(
                IssuerCredRevRecord,
                "retrieve_by_cred_ex_id",
                mock.CoroutineMock(),
            ) as mock_retrieve,
            mock.patch.object(web, "json_response", mock.Mock()) as mock_json_response,
        ):
            mock_retrieve.return_value = mock.MagicMock(
                serialize=mock.MagicMock(return_value="dummy")
            )
            result = await get_cred_rev_record(self.request)

            mock_json_response.assert_called_once_with({"result": "dummy"})
            assert result is mock_json_response.return_value

    async def test_get_cred_rev_record_not_found(self):
        self.request.query = {
            "rev_reg_id": "test_rev_reg_id",
            "cred_rev_id": "1",
        }

        with mock.patch.object(
            IssuerCredRevRecord,
            "retrieve_by_cred_ex_id",
            mock.CoroutineMock(),
        ) as mock_retrieve:
            mock_retrieve.side_effect = StorageNotFoundError("no such rec")
            with self.assertRaises(HTTPNotFound):
                await get_cred_rev_record(self.request)

    async def test_credential_revocation_wrong_profile_403(self):
        """Test that credential revocation endpoints return 403 for wrong profile."""
        self.profile = await create_test_profile(
            settings={"wallet-type": "askar", "admin.admin_api_key": "secret-key"},
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
            headers={"x-api-key": "secret-key"},
        )

        self.request.json = mock.CoroutineMock(
            return_value={
                "rev_reg_id": "rr_id",
                "cred_rev_id": "23",
                "publish": "false",
            }
        )

        # Test revoke endpoint
        with self.assertRaises(HTTPForbidden):
            await revoke(self.request)
