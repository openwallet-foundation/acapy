from unittest import IsolatedAsyncioTestCase

import pytest
from aiohttp import web
from aiohttp.web import HTTPForbidden, HTTPNotFound

from ......admin.request_context import AdminRequestContext
from ......tests import mock
from ......utils.testing import create_test_profile
from .....models.revocation import RevRegDef, RevRegDefValue
from .....revocation.revocation import AnonCredsRevocation
from .....tests.mock_objects import MockRevocationRegistryDefinition
from ....common.testing import BaseAnonCredsRouteTestCaseWithOutbound
from ..routes import get_tails_file, upload_tails_file


@pytest.mark.anoncreds
class TestAnonCredsTailsRoutes(
    BaseAnonCredsRouteTestCaseWithOutbound, IsolatedAsyncioTestCase
):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.rev_reg_id = (
            f"{self.test_did}:4:{self.test_did}:3:CL:1234:default:CL_ACCUM:default"
        )

    async def test_get_tails_file(self):
        self.request.match_info = {"rev_reg_id": self.rev_reg_id}

        with (
            mock.patch.object(
                AnonCredsRevocation,
                "get_created_revocation_registry_definition",
                mock.AsyncMock(),
            ) as mock_get_rev_reg,
            mock.patch.object(web, "FileResponse", mock.Mock()) as mock_file_response,
        ):
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

            result = await get_tails_file(self.request)
            mock_file_response.assert_called_once_with(path="tails_location", status=200)
            assert result is mock_file_response.return_value

    async def test_get_tails_file_not_found(self):
        self.request.match_info = {"rev_reg_id": self.rev_reg_id}

        with (
            mock.patch.object(
                AnonCredsRevocation,
                "get_created_revocation_registry_definition",
                mock.AsyncMock(),
            ) as mock_get_rev_reg,
            mock.patch.object(web, "FileResponse", mock.Mock()) as mock_file_response,
        ):
            mock_get_rev_reg.return_value = None

            with self.assertRaises(HTTPNotFound):
                await get_tails_file(self.request)
            mock_file_response.assert_not_called()

    async def test_tails_wrong_profile_403(self):
        """Test that tails file endpoints return 403 for wrong profile."""
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

        self.request.match_info = {"rev_reg_id": "rev_reg_id"}
        with self.assertRaises(HTTPForbidden):
            await get_tails_file(self.request)

    @mock.patch.object(
        AnonCredsRevocation,
        "get_created_revocation_registry_definition",
        side_effect=[
            MockRevocationRegistryDefinition("revRegId"),
            None,
            MockRevocationRegistryDefinition("revRegId"),
        ],
    )
    @mock.patch.object(
        AnonCredsRevocation,
        "upload_tails_file",
        return_value=None,
    )
    async def test_upload_tails_file(self, mock_upload, mock_get):
        self.request.match_info = {"rev_reg_id": "rev_reg_id"}
        result = await upload_tails_file(self.request)
        assert result is not None
        assert mock_upload.call_count == 1
        assert mock_get.call_count == 1

        with self.assertRaises(HTTPNotFound):
            await upload_tails_file(self.request)

        self.request.match_info = {}

        with self.assertRaises(KeyError):
            await upload_tails_file(self.request)

    async def test_uploads_tails_wrong_profile_403(self):
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

        self.request.match_info = {"rev_reg_id": "rev_reg_id"}
        with self.assertRaises(HTTPForbidden):
            await upload_tails_file(self.request)
