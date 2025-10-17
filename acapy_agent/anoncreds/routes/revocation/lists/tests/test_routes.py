import json
from unittest import IsolatedAsyncioTestCase

import pytest
from aiohttp import web

from ......admin.request_context import AdminRequestContext
from ......anoncreds.revocation import AnonCredsRevocation
from ......tests import mock
from ......utils.testing import create_test_profile
from .....tests.mock_objects import MockRevocationRegistryDefinition
from ....common.testing import BaseAnonCredsRouteTestCase, create_mock_request
from ..routes import rev_list_post


@pytest.mark.anoncreds
class TestAnonCredsRevocationListRoutes(
    BaseAnonCredsRouteTestCase, IsolatedAsyncioTestCase
):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()

    @mock.patch.object(
        AnonCredsRevocation,
        "create_and_register_revocation_list",
        return_value=MockRevocationRegistryDefinition("revRegId"),
    )
    async def test_rev_list_post(self, mock_create):
        self.request.json = mock.CoroutineMock(
            return_value={"rev_reg_def_id": "rev_reg_def_id", "options": {}}
        )
        result = await rev_list_post(self.request)
        assert json.loads(result.body)["revocation_registry_definition_id"] == "revRegId"
        assert mock_create.call_count == 1

    async def test_rev_list_wrong_profile_403(self):
        # Create a profile with wrong type to test the 403 error
        wrong_profile = await create_test_profile(
            settings={"wallet-type": "askar", "admin.admin_api_key": "secret-key"},
        )
        wrong_context = AdminRequestContext.test_context({}, wrong_profile)
        wrong_request = create_mock_request(wrong_context)
        wrong_request.json = mock.CoroutineMock(
            return_value={"rev_reg_def_id": "rev_reg_def_id", "options": {}}
        )

        with self.assertRaises(web.HTTPForbidden):
            await rev_list_post(wrong_request)
