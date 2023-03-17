"""Anoncreds admin routes."""
import logging

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)
from marshmallow import fields
from aries_cloudagent.anoncreds.anoncreds.anoncreds_registry import AnonCredsRegistry
from aries_cloudagent.anoncreds.models.anoncreds_cred_def import (
    AnonCredsCredentialDefinitionValueSchema,
    AnonCredsRegistryGetCredentialDefinitionSchema,
    AnonCredsCredentialDefinitionSchema,
)

from aries_cloudagent.anoncreds.models.anoncreds_schema import (
    AnonCredsSchema,
    PostSchemaResponseSchema,
    SchemaPostQueryStringSchema,
    AnonCredsRegistryGetSchemaSchema,
    SchemasQueryStringSchema,
    SchemasResponseSchema,
)
from aries_cloudagent.anoncreds.models.anoncreds_valid import (
    ANONCREDS_SCHEMA_ID,
    ANONCREDS_VERSION,
)

from ...admin.request_context import AdminRequestContext
from ...messaging.models.openapi import OpenAPISchema
from ...messaging.valid import (
    GENERIC_DID,
    INDY_CRED_DEF_ID,
    INDY_SCHEMA_ID,
    INDY_VERSION,
    UUIDFour,
)

LOGGER = logging.getLogger(__name__)

SPEC_URI = "https://hyperledger.github.io/anoncreds-spec"


class SchemaIdMatchInfo(OpenAPISchema):
    """Path parameters and validators for request taking schema id."""

    schema_id = fields.Str(
        data_key="schemaId", description="Schema identifier", **INDY_SCHEMA_ID
    )


class CredIdMatchInfo(OpenAPISchema):
    """Path parameters and validators for request taking credential id."""

    cred_def_id = fields.Str(
        description="Credential identifier", required=True, example=UUIDFour.EXAMPLE
    )


class CredDefSchema(OpenAPISchema):
    """Parameters and validators for credential definition."""

    # tag = fields.Str(
    #    description="""The tag value passed in by the Issuer to
    #     an AnonCred's Credential Definition create and store implementation."""
    # )
    schemaId = fields.Str(
        data_key="schemaId", description="Schema identifier", **ANONCREDS_SCHEMA_ID
    )
    issuerId = fields.Str(
        description="Issuer Identifier of the credential definition or schema",
        **GENERIC_DID,
    )  # TODO: get correct validator
    supportRevocation = fields.Bool()
    revocationRegistrySize = fields.Int()


class CredDefPostOptionsSchema(OpenAPISchema):
    """Parameters and validators for credential definition options."""

    endorserConnectionId = fields.Str()
    supportRevocation = fields.Bool()
    revocationRegistrySize = fields.Int()


class CredDefPostQueryStringSchema(OpenAPISchema):
    """Parameters and validators for query string in create credential definition."""

    credentialDefinition = fields.Nested(CredDefSchema())
    options = fields.Nested(CredDefPostOptionsSchema())


class CredDefsQueryStringSchema(OpenAPISchema):
    """Parameters and validators for credential definition list query."""

    credentialDefinitionId = fields.Str(
        description="Credential definition identifier",
        **INDY_CRED_DEF_ID,
        data_key="credentialDefinitionId",
    )
    issuer_id = fields.Str(
        description="Issuer Identifier of the credential definition or schema",
        **GENERIC_DID,
        data_key="issuerId",
    )  # TODO: get correct validator
    schema_id = fields.Str(
        data_key="schemaId", description="Schema identifier", **ANONCREDS_SCHEMA_ID
    )
    schema_issuer_id = fields.Str(
        description="Issuer Identifier of the credential definition or schema",
        **GENERIC_DID,
        data_key="schemaIssuerId",
    )  # TODO: get correct validator
    schema_name = fields.Str(
        description="Schema name",
        example=ANONCREDS_SCHEMA_ID["example"].split(":")[2],
        data_key="schemaName",
    )
    schema_version = fields.Str(
        description="Schema version", **ANONCREDS_VERSION, data_key="schemaVersion"
    )


class CredDefState(OpenAPISchema):
    """Parameters and validators for credential definition state."""

    state = fields.Str()  # TODO: create validator for only possible states
    credential_definition_id = fields.Str(
        description="Credential definition identifier",
        **INDY_CRED_DEF_ID,
    )
    credential_definition = fields.Nested(AnonCredsCredentialDefinitionSchema())


class PostCredDefResponseSchema(OpenAPISchema):
    """Parameters and validators for credential definition create response."""

    job_id = fields.Str()
    credential_definition_state = fields.Nested(CredDefState())
    registration_metadata = fields.Dict()
    credential_definition_metadata = fields.Dict()


class GetCredDefsResponseSchema(OpenAPISchema):
    """Parameters and validators for credential definition list all response."""

    credential_definition_id = fields.Str()


@docs(tags=["anoncreds"], summary="")
@request_schema(SchemaPostQueryStringSchema())
@response_schema(PostSchemaResponseSchema(), 200, description="")
async def schemas_post(request: web.BaseRequest):
    """Request handler for creating a schema.

    Args:
        request (web.BaseRequest): aiohttp request object
          schema: {
                "attrNames": ["string"],
                "name": "string",
                "version": "string",
                "issuerId": "string"
            },
        options: options method can be different per method,
            but it can also include default options for all anoncreds
            methods (none for schema). it can also be automatically
            inferred from the agent startup parameters (default endorser)
            endorser_connection_id: ""
    Returns:
        json object:
            job_id: job identifier to keep track of the status of the schema creation.
            MUST be absent or have a null value if the value of the schema_state. state
            response field is either finished or failed, and MUST NOT have a null value
            otherwise.
            schema_state:
                state : The state of the schema creation. Possible values are finished,
                failed, action and wait.
                schema_id : The id of the schema. If the value of the schema_state.state
                response field is finished, this field MUST be present and MUST NOT have
                a null value.
                schema : The schema. If the value of the schema_state.state response field
                is finished, this field MUST be present and MUST NOT have a null value.
            registration_metadata : This field contains metadata about hte registration
            process
            schema_metadata : This fields contains metadata about the schema.

    """
    context: AdminRequestContext = request["context"]
    anon_creds_registry = context.inject(AnonCredsRegistry)
    request_data = await request.json()
    options = request_data.get("option")
    schema_data = request_data.get("schema")

    schema: AnonCredsSchema = AnonCredsSchema(
        issuer_id=schema_data.get("issuerId"),
        attr_names=schema_data.get("attrNames"),
        name=schema_data.get("name"),
        version=schema_data.get("version"),
    )
    result = anon_creds_registry.register_schema(options, schema)
    return web.json_response(result)


@docs(tags=["anoncreds"], summary="")
@match_info_schema(SchemaIdMatchInfo())
@response_schema(AnonCredsRegistryGetSchemaSchema(), 200, description="")
async def schema_get(request: web.BaseRequest):
    """Request handler for getting a schema.

    Args:
        request (web.BaseRequest): aiohttp request object

    Returns:
        json object: schema

    """
    context: AdminRequestContext = request["context"]
    anon_creds_registry = context.inject(AnonCredsRegistry)
    schema_id = request.match_info["schemaId"]
    result = await anon_creds_registry.get_schema(schema_id)

    return web.json_response(result)


@docs(tags=["anoncreds"], summary="")
@querystring_schema(SchemasQueryStringSchema())
@response_schema(SchemasResponseSchema(), 200, description="")
async def schemas_get(request: web.BaseRequest):
    """Request handler for getting all schemas.

    Args:

    Returns:

    """
    context: AdminRequestContext = request["context"]
    anon_creds_registry = context.inject(AnonCredsRegistry)
    schema_issuer_did = request.query.get("schemaIssuerDid")
    schema_name = request.query.get("schemaName")
    schema_version = request.query.get("schemaVersion")
    filter = {
        "issuerId": schema_issuer_did,
        "name": schema_name,
        "version": schema_version,
    }
    schema_ids = anon_creds_registry.get_schemas(filter)
    return web.json_response(schema_ids)


@docs(tags=["anoncreds"], summary="")
@request_schema(CredDefPostQueryStringSchema())
@response_schema(PostCredDefResponseSchema(), 200, description="")
async def cred_def_post(request: web.BaseRequest):
    """Request handler for creating .

    Args:

    Returns:

    """
    context: AdminRequestContext = request["context"]
    anon_creds_registry = context.inject(AnonCredsRegistry)
    request_data = await request.json()
    options = request_data.get("option")
    data = request_data.get("credentialDefinition")

    cred_def = {
        "issuer_id": data.get("issuerId"),
        "schema_id": data.get("schemaId"),
        # "tag":data.get("tag"),
        "support_revocation": data.get("supportRevocation"),
        "revocation_registrySize": data.get("revocationRegistrySize"),
    }
    result = anon_creds_registry.register_credential_definition(options, cred_def)
    parameters = await request.json()
    return web.json_response(result)


@docs(tags=["anoncreds"], summary="")
@match_info_schema(CredIdMatchInfo())
@response_schema(AnonCredsRegistryGetCredentialDefinitionSchema(), 200, description="")
async def cred_def_get(request: web.BaseRequest):
    """Request handler for getting credential definition.

    Args:

    Returns:

    """
    context: AdminRequestContext = request["context"]
    anon_creds_registry = context.inject(AnonCredsRegistry)
    credential_id = request.match_info["cred_def_id"]
    result = await anon_creds_registry.get_credential_definition(credential_id)
    return web.json_response(result)


@docs(tags=["anoncreds"], summary="")
@querystring_schema(CredDefsQueryStringSchema())
@response_schema(GetCredDefsResponseSchema(), 200, description="")
async def cred_defs_get(request: web.BaseRequest):
    """Request handler for getting all credential definitions.

    Args:

    Returns:

    """
    context: AdminRequestContext = request["context"]
    anon_creds_registry = context.inject(AnonCredsRegistry)
    query = request.query

    filter = {
        "cred_def_id": query.get("credentialDefinitionId"),
        "issuer_id": query.get("issuerId"),
        "schema_id": query.get("schemaId"),
        "schema_issuer_id": query.get("schemaIssuerId"),
        "schema_name": query.get("schemaName"),
        "schema_version": query.get("schemaVersion"),
    }
    cred_def_ids = anon_creds_registry.get_credential_definitions(filter)
    return web.json_response(cred_def_ids)


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/anoncreds/schema", schemas_post),
            web.get("/anoncreds/schema/{schemaId}", schema_get, allow_head=False),
            web.get("/anoncreds/schemas", schemas_get, allow_head=False),
            web.post("/anoncreds/credential-definition", cred_def_post),
            web.get(
                "/anoncreds/credential-definition/{cred_def_id}",
                cred_def_get,
                allow_head=False,
            ),
            web.get(
                "/anoncreds/credential-definitions/",
                cred_defs_get,
                allow_head=False,
            ),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "anoncreds",
            "description": "Anoncreds management",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
