import json
from unittest import IsolatedAsyncioTestCase

import pytest
from aiohttp import web

from .....admin.request_context import AdminRequestContext
from .....tests import mock
from .....utils.testing import create_test_profile
from ....base import AnonCredsObjectNotFound
from ....issuer import AnonCredsIssuer
from ....models.schema import AnonCredsSchema, SchemaResult, SchemaState
from ...common.testing import BaseAnonCredsRouteTestCase, create_mock_request
from ..routes import schema_get, schemas_get, schemas_post


class MockSchema:
    def __init__(self, schema_id):
        self.schema_id = schema_id

    def serialize(self):
        return {"schema_id": self.schema_id}


@pytest.mark.anoncreds
class TestAnonCredsSchemaRoutes(BaseAnonCredsRouteTestCase, IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()

    @mock.patch.object(
        AnonCredsIssuer,
        "create_and_register_schema",
        return_value=SchemaResult(
            job_id=None,
            schema_state=SchemaState(
                state="finished",
                schema_id=None,
                schema=AnonCredsSchema(
                    issuer_id="issuer-id",
                    name="name",
                    version="1.0",
                    attr_names=["attr1", "attr2"],
                ),
            ),
        ),
    )
    async def test_schemas_post(self, mock_create_and_register_schema):
        self.request.json = mock.CoroutineMock(
            side_effect=[
                {
                    "schema": {
                        "issuerId": "Q4TmbeGPoWeWob4Xf6KetA",
                        "attrNames": ["score"],
                        "name": "Example Schema",
                        "version": "0.0.1",
                    }
                },
                {},
                {"schema": {}},
                {
                    "schema": {
                        "attrNames": ["score"],
                        "name": "Example Schema",
                        "version": "0.0.1",
                    }
                },
            ]
        )
        result = await schemas_post(self.request)
        assert result is not None

        assert mock_create_and_register_schema.call_count == 1

        with self.assertRaises(web.HTTPBadRequest):
            # Empty body
            await schemas_post(self.request)
            # Empty schema
            await schemas_post(self.request)
            # Missing issuerId
            await schemas_post(self.request)

    async def test_get_schema(self):
        self.request.match_info = {"schema_id": "schema_id"}
        self.context.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_schema=mock.CoroutineMock(
                    side_effect=[
                        MockSchema("schemaId"),
                        AnonCredsObjectNotFound("test"),
                    ]
                )
            )
        )
        result = await schema_get(self.request)
        assert json.loads(result.body)["schema_id"] == "schemaId"

        # missing schema_id
        self.request.match_info = {}
        with self.assertRaises(KeyError):
            await schema_get(self.request)

        # schema not found
        self.request.match_info = {"schema_id": "schema_id"}
        with self.assertRaises(web.HTTPNotFound):
            await schema_get(self.request)

    @mock.patch.object(
        AnonCredsIssuer,
        "get_created_schemas",
        side_effect=[
            [
                "Q4TmbeGPoWeWob4Xf6KetA:2:Example Schema:0.0.1",
                "Q4TmbeGPoWeWob4Xf6KetA:2:Example Schema:0.0.2",
            ],
            [],
        ],
    )
    async def test_get_schemas(self, mock_get_created_schemas):
        result = await schemas_get(self.request)
        assert json.loads(result.body)["schema_ids"].__len__() == 2

        result = await schemas_get(self.request)
        assert json.loads(result.body)["schema_ids"].__len__() == 0

        assert mock_get_created_schemas.call_count == 2

    async def test_schema_endpoints_wrong_profile_403(self):
        # Create a profile with wrong type to test the 403 error
        wrong_profile = await create_test_profile(
            settings={"wallet-type": "askar", "admin.admin_api_key": "secret-key"},
        )
        wrong_context = AdminRequestContext.test_context({}, wrong_profile)
        wrong_request = create_mock_request(wrong_context)

        # POST schema
        wrong_request.json = mock.CoroutineMock(
            return_value={
                "schema": {
                    "issuerId": "Q4TmbeGPoWeWob4Xf6KetA",
                    "attrNames": ["score"],
                    "name": "Example Schema",
                    "version": "0.0.1",
                }
            }
        )
        with self.assertRaises(web.HTTPForbidden):
            await schemas_post(wrong_request)

        # GET schema
        wrong_request.match_info = {"schema_id": "schema_id"}
        with self.assertRaises(web.HTTPForbidden):
            await schema_get(wrong_request)

        # GET schemas
        with self.assertRaises(web.HTTPForbidden):
            await schemas_get(wrong_request)
