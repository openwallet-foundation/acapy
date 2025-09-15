import json
from unittest import IsolatedAsyncioTestCase

import pytest
from aiohttp import web

from .....admin.request_context import AdminRequestContext
from .....tests import mock
from .....utils.testing import create_test_profile
from ....issuer import AnonCredsIssuer
from ...common.testing import BaseAnonCredsRouteTestCase, create_mock_request
from ..routes import cred_def_get, cred_def_post, cred_defs_get


class MockCredentialDefinition:
    def __init__(self, cred_def_id):
        self.cred_def_id = cred_def_id

    def serialize(self):
        return {"credential_definition_id": self.cred_def_id}


@pytest.mark.anoncreds
class TestAnonCredsCredDefRoutes(BaseAnonCredsRouteTestCase, IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()

    @mock.patch.object(
        AnonCredsIssuer,
        "create_and_register_credential_definition",
        return_value=MockCredentialDefinition("credDefId"),
    )
    async def test_cred_def_post(self, mock_create_cred_def):
        self.request.json = mock.CoroutineMock(
            side_effect=[
                {
                    "credential_definition": {
                        "issuerId": "issuerId",
                        "schemaId": "schemaId",
                        "tag": "tag",
                    },
                    "options": {
                        "endorser_connection_id": "string",
                        "revocation_registry_size": 0,
                        "support_revocation": True,
                    },
                },
                {},
                {"credential_definition": {}},
            ]
        )

        result = await cred_def_post(self.request)

        assert json.loads(result.body)["credential_definition_id"] == "credDefId"
        assert mock_create_cred_def.call_count == 1

        with self.assertRaises(web.HTTPBadRequest):
            await cred_def_post(self.request)

        await cred_def_post(self.request)

    async def test_cred_def_get(self):
        self.request.match_info = {"cred_def_id": "cred_def_id"}
        self.context.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_credential_definition=mock.CoroutineMock(
                    return_value=MockCredentialDefinition("credDefId")
                )
            )
        )
        result = await cred_def_get(self.request)
        assert json.loads(result.body)["credential_definition_id"] == "credDefId"

        self.request.match_info = {}
        with self.assertRaises(KeyError):
            await cred_def_get(self.request)

    @mock.patch.object(
        AnonCredsIssuer,
        "get_created_credential_definitions",
        side_effect=[
            [
                "Q4TmbeGPoWeWob4Xf6KetA:3:CL:229927:tag",
                "Q4TmbeGPoWeWob4Xf6KetA:3:CL:229925:faber.agent.degree_schema",
            ],
            [],
        ],
    )
    async def test_cred_defs_get(self, mock_get_cred_defs):
        result = await cred_defs_get(self.request)
        assert len(json.loads(result.body)["credential_definition_ids"]) == 2

        result = await cred_defs_get(self.request)
        assert len(json.loads(result.body)["credential_definition_ids"]) == 0

        assert mock_get_cred_defs.call_count == 2

    async def test_cred_def_endpoints_wrong_profile_403(self):
        # Create a profile with wrong type to test the 403 error
        wrong_profile = await create_test_profile(
            settings={"wallet-type": "askar", "admin.admin_api_key": "secret-key"},
        )
        wrong_context = AdminRequestContext.test_context({}, wrong_profile)
        wrong_request = create_mock_request(wrong_context)

        # POST cred def
        wrong_request.json = mock.CoroutineMock(
            return_value={
                "credential_definition": {
                    "issuerId": "issuerId",
                    "schemaId": "schemaId",
                    "tag": "tag",
                },
                "options": {
                    "revocation_registry_size": 0,
                    "support_revocation": True,
                },
            }
        )
        with self.assertRaises(web.HTTPForbidden):
            await cred_def_post(wrong_request)

        # GET cred def
        wrong_request.match_info = {"cred_def_id": "cred_def_id"}
        with self.assertRaises(web.HTTPForbidden):
            await cred_def_get(wrong_request)

        # GET cred defs
        with self.assertRaises(web.HTTPForbidden):
            await cred_defs_get(wrong_request)
