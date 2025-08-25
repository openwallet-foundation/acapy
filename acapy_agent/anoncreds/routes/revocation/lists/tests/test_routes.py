import json
from unittest import IsolatedAsyncioTestCase

import pytest
from aiohttp import web

from acapy_agent.anoncreds.tests.mock_objects import MockRevocationRegistryDefinition

from ......admin.request_context import AdminRequestContext
from ......anoncreds.revocation import AnonCredsRevocation
from ......tests import mock
from ......utils.testing import create_test_profile
from ..routes import rev_list_post


@pytest.mark.anoncreds
class TestAnonCredsRevocationListRoutes(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.session_inject = {}
        self.profile = await create_test_profile(
            settings={
                "wallet.type": "askar-anoncreds",
                "admin.admin_api_key": "secret-key",
            },
        )
        self.context = AdminRequestContext.test_context(self.session_inject, self.profile)
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

    @mock.patch.object(
        AnonCredsRevocation,
        "create_and_register_revocation_list",
        return_value=MockRevocationRegistryDefinition("revRegId"),
    )
    async def test_rev_list_post(self, mock_create):
        self.request.json = mock.CoroutineMock(
            return_value={"revRegDefId": "rev_reg_def_id", "options": {}}
        )
        result = await rev_list_post(self.request)
        assert json.loads(result.body)["revocation_registry_definition_id"] == "revRegId"
        assert mock_create.call_count == 1

    async def test_rev_list_wrong_profile_403(self):
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
            return_value={"revRegDefId": "rev_reg_def_id", "options": {}}
        )
        with self.assertRaises(web.HTTPForbidden):
            await rev_list_post(self.request)
