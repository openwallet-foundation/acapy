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

from .anoncreds_registry import AnonCredsRegistry
from ..issuer import AnonCredsIssuer
from ..models.anoncreds_cred_def import (
    CredDefSchema,
    GetCredDefResultSchema,
)
from ..models.anoncreds_schema import (
    AnonCredsSchemaSchema,
    SchemaResultSchema,
    GetSchemaResultSchema,
)

from ...admin.request_context import AdminRequestContext
from ...messaging.models.openapi import OpenAPISchema
from ...messaging.valid import (
    UUIDFour,
)

LOGGER = logging.getLogger(__name__)

SPEC_URI = "https://hyperledger.github.io/anoncreds-spec"


class SchemaIdMatchInfo(OpenAPISchema):
    """Path parameters and validators for request taking schema id."""

    schema_id = fields.Str(data_key="schemaId", description="Schema identifier")


class CredIdMatchInfo(OpenAPISchema):
    """Path parameters and validators for request taking credential id."""

    cred_def_id = fields.Str(
        description="Credential identifier", required=True, example=UUIDFour.EXAMPLE
    )


class InnerCredDefSchema(OpenAPISchema):
    """Parameters and validators for credential definition."""

    tag = fields.Str(description="Credential definition tag")
    schemaId = fields.Str(data_key="schemaId", description="Schema identifier")
    issuerId = fields.Str(
        description="Issuer Identifier of the credential definition or schema",
    )


class CredDefPostOptionsSchema(OpenAPISchema):
    """Parameters and validators for credential definition options."""

    endorser_connection_id = fields.Str(required=False)
    support_revocation = fields.Bool(required=False)
    revocation_registry_size = fields.Int(required=False)


class CredDefPostRequestSchema(OpenAPISchema):
    """Parameters and validators for query string in create credential definition."""

    credential_definition = fields.Nested(InnerCredDefSchema())
    options = fields.Nested(CredDefPostOptionsSchema())


class CredDefsQueryStringSchema(OpenAPISchema):
    """Parameters and validators for credential definition list query."""

    issuer_id = fields.Str(
        description="Issuer Identifier of the credential definition",
    )
    schema_id = fields.Str(data_key="schemaId", description="Schema identifier")
    schema_name = fields.Str(
        description="Schema name",
    )
    schema_version = fields.Str(description="Schema version")
    state = fields.Str(
        description="Credential definition state",
    )


class CredDefState(OpenAPISchema):
    """Parameters and validators for credential definition state."""

    state = fields.Str()  # TODO: create validator for only possible states
    credential_definition_id = fields.Str(
        description="Credential definition identifier",
    )
    credential_definition = fields.Nested(CredDefSchema())


class PostCredDefResponseSchema(OpenAPISchema):
    """Parameters and validators for credential definition create response."""

    job_id = fields.Str()
    credential_definition_state = fields.Nested(CredDefState())
    registration_metadata = fields.Dict()
    credential_definition_metadata = fields.Dict()


class SchemaPostOptionSchema(OpenAPISchema):
    """Parameters and validators for schema options."""

    endorser_connection_id = fields.UUID(
        description="Connection identifier (optional) (this is an example)",
        required=False,
        example=UUIDFour.EXAMPLE,
    )


class SchemaPostRequestSchema(OpenAPISchema):
    """Parameters and validators for query string in create schema."""

    schema = fields.Nested(AnonCredsSchemaSchema())
    options = fields.Nested(SchemaPostOptionSchema())


@docs(tags=["anoncreds"], summary="")
@request_schema(SchemaPostRequestSchema())
@response_schema(SchemaResultSchema(), 200, description="")
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

    body = await request.json()
    options = body.get("option")
    schema_data = body.get("schema")

    issuer_id = schema_data.get("issuerId")
    attr_names = schema_data.get("attrNames")
    name = schema_data.get("name")
    version = schema_data.get("version")

    issuer = context.inject(AnonCredsIssuer)
    result = await issuer.create_and_register_schema(
        issuer_id, name, version, attr_names, options=options
    )
    return web.json_response(result.serialize())


@docs(tags=["anoncreds"], summary="")
@match_info_schema(SchemaIdMatchInfo())
@response_schema(GetSchemaResultSchema(), 200, description="")
async def schema_get(request: web.BaseRequest):
    """Request handler for getting a schema.

    Args:
        request (web.BaseRequest): aiohttp request object

    Returns:
        json object: schema

    """
    context: AdminRequestContext = request["context"]
    anoncreds_registry = context.inject(AnonCredsRegistry)
    schema_id = request.match_info["schemaId"]
    result = await anoncreds_registry.get_schema(context.profile, schema_id)

    return web.json_response(result.serialize())


class SchemasQueryStringSchema(OpenAPISchema):
    """Parameters and validators for query string in schemas list query."""

    schema_name = fields.Str(
        description="Schema name",
        example="example-schema",
    )
    schema_version = fields.Str(description="Schema version")
    schema_issuer_id = fields.Str(
        description="Issuer Identifier of the credential definition or schema",
    )


class GetSchemasResponseSchema(OpenAPISchema):
    """Parameters and validators for schema list all response."""

    schema_ids = fields.List(
        fields.Str(
            data_key="schemaIds",
            description="Schema identifier",
        )
    )


@docs(tags=["anoncreds"], summary="")
@querystring_schema(SchemasQueryStringSchema())
@response_schema(GetSchemasResponseSchema(), 200, description="")
async def schemas_get(request: web.BaseRequest):
    """Request handler for getting all schemas.

    Args:

    Returns:

    """
    context: AdminRequestContext = request["context"]

    schema_issuer_id = request.query.get("schema_issuer_id")
    schema_name = request.query.get("schema_name")
    schema_version = request.query.get("schema_version")

    issuer = context.inject(AnonCredsIssuer)
    schema_ids = await issuer.get_created_schemas(
        schema_name, schema_version, schema_issuer_id
    )
    return web.json_response({"schema_ids": schema_ids})


@docs(tags=["anoncreds"], summary="")
@request_schema(CredDefPostRequestSchema())
@response_schema(PostCredDefResponseSchema(), 200, description="")
async def cred_def_post(request: web.BaseRequest):
    """Request handler for creating .

    Args:

    Returns:

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    options = body.get("options")
    cred_def = body.get("credential_definition")
    issuer_id = cred_def.get("issuerId")
    schema_id = cred_def.get("schemaId")
    tag = cred_def.get("tag")

    issuer = context.inject(AnonCredsIssuer)
    result = await issuer.create_and_store_credential_definition(
        issuer_id,
        schema_id,
        tag,
        options=options,
    )

    return web.json_response(result.serialize())


@docs(tags=["anoncreds"], summary="")
@match_info_schema(CredIdMatchInfo())
@response_schema(GetCredDefResultSchema(), 200, description="")
async def cred_def_get(request: web.BaseRequest):
    """Request handler for getting credential definition.

    Args:

    Returns:

    """
    context: AdminRequestContext = request["context"]
    anon_creds_registry = context.inject(AnonCredsRegistry)
    credential_id = request.match_info["cred_def_id"]
    result = await anon_creds_registry.get_credential_definition(
        context.profile, credential_id
    )
    return web.json_response(result.serialize())


class GetCredDefsResponseSchema(OpenAPISchema):
    """AnonCredsRegistryGetCredDefsSchema"""

    credential_definition_ids = fields.List(
        fields.Str(
            description="credential definition identifiers",
        )
    )


@docs(tags=["anoncreds"], summary="")
@querystring_schema(CredDefsQueryStringSchema())
@response_schema(GetCredDefsResponseSchema(), 200, description="")
async def cred_defs_get(request: web.BaseRequest):
    """Request handler for getting all credential definitions.

    Args:

    Returns:

    """
    context: AdminRequestContext = request["context"]
    issuer = context.inject(AnonCredsIssuer)

    cred_def_ids = await issuer.get_created_credential_definitions(
        issuer_id=request.query.get("issuer_id"),
        schema_id=request.query.get("schema_id"),
        schema_name=request.query.get("schema_name"),
        schema_version=request.query.get("schema_version"),
        state=request.query.get("state"),
    )
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
