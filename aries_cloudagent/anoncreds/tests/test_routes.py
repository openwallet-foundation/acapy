import json
from unittest import IsolatedAsyncioTestCase

import pytest
from aiohttp import web

from aries_cloudagent.admin.request_context import AdminRequestContext
from aries_cloudagent.anoncreds.base import AnonCredsObjectNotFound
from aries_cloudagent.anoncreds.issuer import AnonCredsIssuer
from aries_cloudagent.anoncreds.models.anoncreds_schema import (
    AnonCredsSchema,
    SchemaResult,
    SchemaState,
)
from aries_cloudagent.anoncreds.revocation import AnonCredsRevocation
from aries_cloudagent.anoncreds.revocation_setup import DefaultRevocationSetup
from aries_cloudagent.askar.profile_anon import AskarAnoncredsProfile
from aries_cloudagent.core.event_bus import MockEventBus
from aries_cloudagent.core.in_memory.profile import (
    InMemoryProfile,
)
from aries_cloudagent.tests import mock

from ...askar.profile import AskarProfile
from .. import routes as test_module


class MockSchema:
    def __init__(self, schema_id):
        self.schemaId = schema_id

    def serialize(self):
        return {"schema_id": self.schemaId}


class MockCredentialDefinition:
    def __init__(self, cred_def_id):
        self.credDefId = cred_def_id

    def serialize(self):
        return {"credential_definition_id": self.credDefId}


class MockRovocationRegistryDefinition:
    def __init__(self, rev_reg_id):
        self.revRegId = rev_reg_id

    def serialize(self):
        return {"revocation_registry_definition_id": self.revRegId}


@pytest.mark.anoncreds
class TestAnoncredsRoutes(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.session_inject = {}
        self.profile = InMemoryProfile.test_profile(
            settings={"wallet.type": "askar-anoncreds"},
            profile_class=AskarAnoncredsProfile,
        )
        self.context = AdminRequestContext.test_context(
            self.session_inject, self.profile
        )
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
            ]
        )
        result = await test_module.schemas_post(self.request)
        assert result is not None

        assert mock_create_and_register_schema.call_count == 1

        with self.assertRaises(web.HTTPBadRequest):
            await test_module.schemas_post(self.request)

        await test_module.schemas_post(self.request)

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
        result = await test_module.schema_get(self.request)
        assert json.loads(result.body)["schema_id"] == "schemaId"

        # missing schema_id
        self.request.match_info = {}
        with self.assertRaises(KeyError):
            await test_module.schema_get(self.request)

        # schema not found
        self.request.match_info = {"schema_id": "schema_id"}
        with self.assertRaises(web.HTTPNotFound):
            await test_module.schema_get(self.request)

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
        result = await test_module.schemas_get(self.request)
        assert json.loads(result.body)["schema_ids"].__len__() == 2

        result = await test_module.schemas_get(self.request)
        assert json.loads(result.body)["schema_ids"].__len__() == 0

        assert mock_get_created_schemas.call_count == 2

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

        result = await test_module.cred_def_post(self.request)

        assert json.loads(result.body)["credential_definition_id"] == "credDefId"
        assert mock_create_cred_def.call_count == 1

        with self.assertRaises(web.HTTPBadRequest):
            await test_module.cred_def_post(self.request)

        await test_module.cred_def_post(self.request)

    async def test_cred_def_get(self):
        self.request.match_info = {"cred_def_id": "cred_def_id"}
        self.context.inject = mock.Mock(
            return_value=mock.MagicMock(
                get_credential_definition=mock.CoroutineMock(
                    return_value=MockCredentialDefinition("credDefId")
                )
            )
        )
        result = await test_module.cred_def_get(self.request)
        assert json.loads(result.body)["credential_definition_id"] == "credDefId"

        self.request.match_info = {}
        with self.assertRaises(KeyError):
            await test_module.cred_def_get(self.request)

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
        result = await test_module.cred_defs_get(self.request)
        assert len(json.loads(result.body)["credential_definition_ids"]) == 2

        result = await test_module.cred_defs_get(self.request)
        assert len(json.loads(result.body)["credential_definition_ids"]) == 0

        assert mock_get_cred_defs.call_count == 2

    @mock.patch.object(
        AnonCredsIssuer,
        "match_created_credential_definitions",
        side_effect=["found", None],
    )
    @mock.patch.object(
        AnonCredsRevocation,
        "create_and_register_revocation_registry_definition",
        return_value=MockRovocationRegistryDefinition("revRegId"),
    )
    async def test_rev_reg_def_post(self, mock_match, mock_create):
        self.request.json = mock.CoroutineMock(
            return_value={
                "credDefId": "cred_def_id",
                "issuerId": "issuer_id",
                "maxCredNum": 100,
                "options": {
                    "tails_public_uri": "http://tails_public_uri",
                    "tails_local_uri": "http://tails_local_uri",
                },
            }
        )

        # Must be in wrapper object
        with self.assertRaises(web.HTTPBadRequest):
            await test_module.rev_reg_def_post(self.request)

        self.request.json = mock.CoroutineMock(
            return_value={
                "revocation_registry_definition": {
                    "credDefId": "cred_def_id",
                    "issuerId": "issuer_id",
                    "maxCredNum": 100,
                    "options": {
                        "tails_public_uri": "http://tails_public_uri",
                        "tails_local_uri": "http://tails_local_uri",
                    },
                }
            }
        )

        result = await test_module.rev_reg_def_post(self.request)

        assert (
            json.loads(result.body)["revocation_registry_definition_id"] == "revRegId"
        )

        assert mock_match.call_count == 1
        assert mock_create.call_count == 1

        with self.assertRaises(web.HTTPNotFound):
            await test_module.rev_reg_def_post(self.request)

    @mock.patch.object(
        AnonCredsRevocation,
        "create_and_register_revocation_list",
        return_value=MockRovocationRegistryDefinition("revRegId"),
    )
    async def test_rev_list_post(self, mock_create):
        self.request.json = mock.CoroutineMock(
            return_value={"revRegDefId": "rev_reg_def_id", "options": {}}
        )
        result = await test_module.rev_list_post(self.request)
        assert (
            json.loads(result.body)["revocation_registry_definition_id"] == "revRegId"
        )
        assert mock_create.call_count == 1

    @mock.patch.object(
        AnonCredsRevocation,
        "get_created_revocation_registry_definition",
        side_effect=[
            MockRovocationRegistryDefinition("revRegId"),
            None,
            MockRovocationRegistryDefinition("revRegId"),
        ],
    )
    @mock.patch.object(
        AnonCredsRevocation,
        "upload_tails_file",
        return_value=None,
    )
    async def test_upload_tails_file(self, mock_upload, mock_get):
        self.request.match_info = {"rev_reg_id": "rev_reg_id"}
        result = await test_module.upload_tails_file(self.request)
        assert result is not None
        assert mock_upload.call_count == 1
        assert mock_get.call_count == 1

        with self.assertRaises(web.HTTPNotFound):
            await test_module.upload_tails_file(self.request)

        self.request.match_info = {}

        with self.assertRaises(KeyError):
            await test_module.upload_tails_file(self.request)

    @mock.patch.object(
        AnonCredsRevocation,
        "set_active_registry",
        return_value=None,
    )
    async def test_set_active_registry(self, mock_set):
        self.request.match_info = {"rev_reg_id": "rev_reg_id"}
        await test_module.set_active_registry(self.request)
        assert mock_set.call_count == 1

        self.request.match_info = {}
        with self.assertRaises(KeyError):
            await test_module.set_active_registry(self.request)

    async def test_schema_endpoints_wrong_profile_403(self):
        self.profile = InMemoryProfile.test_profile(
            settings={"wallet-type": "askar"},
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

        # POST schema
        self.request.json = mock.CoroutineMock(
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
            await test_module.schemas_post(self.request)

        # GET schema
        self.request.match_info = {"schema_id": "schema_id"}
        with self.assertRaises(web.HTTPForbidden):
            await test_module.schema_get(self.request)

        # GET schemas
        with self.assertRaises(web.HTTPForbidden):
            await test_module.schemas_get(self.request)

    async def test_cred_def_endpoints_wrong_profile_403(self):
        self.profile = InMemoryProfile.test_profile(
            settings={"wallet-type": "askar"},
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

        # POST cred def
        self.request.json = mock.CoroutineMock(
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
            await test_module.cred_def_post(self.request)

        # GET cred def
        self.request.match_info = {"cred_def_id": "cred_def_id"}
        with self.assertRaises(web.HTTPForbidden):
            await test_module.cred_def_get(self.request)

        # GET cred defs
        with self.assertRaises(web.HTTPForbidden):
            await test_module.cred_defs_get(self.request)

    async def test_rev_reg_wrong_profile_403(self):
        self.profile = InMemoryProfile.test_profile(
            settings={"wallet-type": "askar"},
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
                "revocation_registry_definition": {
                    "credDefId": "cred_def_id",
                    "issuerId": "issuer_id",
                    "maxCredNum": 100,
                },
                "options": {
                    "tails_public_uri": "http://tails_public_uri",
                    "tails_local_uri": "http://tails_local_uri",
                },
            }
        )
        with self.assertRaises(web.HTTPForbidden):
            await test_module.rev_reg_def_post(self.request)

    async def test_rev_list_wrong_profile_403(self):
        self.profile = InMemoryProfile.test_profile(
            settings={"wallet-type": "askar"},
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
            return_value={"revRegDefId": "rev_reg_def_id", "options": {}}
        )
        with self.assertRaises(web.HTTPForbidden):
            await test_module.rev_list_post(self.request)

    async def test_uploads_tails_wrong_profile_403(self):
        self.profile = InMemoryProfile.test_profile(
            settings={"wallet-type": "askar"},
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

        self.request.match_info = {"rev_reg_id": "rev_reg_id"}
        with self.assertRaises(web.HTTPForbidden):
            await test_module.upload_tails_file(self.request)

    async def test_active_registry_wrong_profile_403(self):
        self.profile = InMemoryProfile.test_profile(
            settings={"wallet-type": "askar"},
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

        self.request.match_info = {"rev_reg_id": "rev_reg_id"}

        with self.assertRaises(web.HTTPForbidden):
            await test_module.set_active_registry(self.request)

    @mock.patch.object(DefaultRevocationSetup, "register_events")
    async def test_register_events(self, mock_revocation_setup_listeners):
        mock_event_bus = MockEventBus()
        mock_event_bus.subscribe = mock.MagicMock()
        test_module.register_events(mock_event_bus)
        assert mock_revocation_setup_listeners.call_count == 1

    async def test_register(self):
        mock_app = mock.MagicMock()
        mock_app.add_routes = mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
