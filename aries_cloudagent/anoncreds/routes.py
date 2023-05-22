"""Anoncreds admin routes."""
from asyncio import shield
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
from aries_cloudagent.askar.profile import AskarProfile

from aries_cloudagent.revocation.routes import (
    RevRegIdMatchInfoSchema,
    RevocationModuleResponseSchema,
)

from ..admin.request_context import AdminRequestContext
from ..messaging.models.openapi import OpenAPISchema
from ..messaging.valid import UUIDFour
from ..revocation.anoncreds import AnonCredsRevocation
from ..revocation.error import RevocationNotSupportedError
from ..storage.error import StorageNotFoundError
from .issuer import AnonCredsIssuer, AnonCredsIssuerError
from .models.anoncreds_cred_def import CredDefResultSchema, GetCredDefResultSchema
from .models.anoncreds_revocation import (
    GetRevRegDefResult,
    RevRegDef,
    RevRegDefResultSchema,
    RevListResultSchema,
)
from .models.anoncreds_schema import (
    AnonCredsSchemaSchema,
    GetSchemaResultSchema,
    SchemaResultSchema,
)
from .registry import AnonCredsRegistry

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

    issuer = AnonCredsIssuer(context.profile)
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

    issuer = AnonCredsIssuer(context.profile)
    schema_ids = await issuer.get_created_schemas(
        schema_name, schema_version, schema_issuer_id
    )
    return web.json_response({"schema_ids": schema_ids})


@docs(tags=["anoncreds"], summary="")
@request_schema(CredDefPostRequestSchema())
@response_schema(CredDefResultSchema(), 200, description="")
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

    issuer = AnonCredsIssuer(context.profile)
    result = await issuer.create_and_register_credential_definition(
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
    issuer = AnonCredsIssuer(context.profile)

    cred_def_ids = await issuer.get_created_credential_definitions(
        issuer_id=request.query.get("issuer_id"),
        schema_id=request.query.get("schema_id"),
        schema_name=request.query.get("schema_name"),
        schema_version=request.query.get("schema_version"),
    )
    return web.json_response(cred_def_ids)


class RevRegCreateRequestSchema(OpenAPISchema):
    """Request schema for revocation registry creation request."""

    issuer_id = fields.Str(
        description="Issuer Identifier of the credential definition or schema",
        data_key="issuerId",
    )
    cred_def_id = fields.Str(
        description="Credential definition identifier",
        data_key="credDefId",
    )
    tag = fields.Str(description="tag for revocation registry")
    max_cred_num = fields.Int(data_key="maxCredNum")
    registry_type = fields.Str(
        description="Revocation registry type",
        data_key="type",
        required=False,
    )


@docs(tags=["anoncreds"], summary="")
@request_schema(RevRegCreateRequestSchema())
@response_schema(RevRegDefResultSchema(), 200, description="")
async def rev_reg_def_post(request: web.BaseRequest):
    """Request handler for creating .

    Args:


    (method) def create_and_register_revocation_registry_definition(
        issuer_id: str,
        cred_def_id: str,
        tag: str,
        max_cred_num: int,
        registry_type: str,
        tails_base_path: str,
        options: dict[Unknown, Unknown] | None = None
    ) -> Coroutine[Any, Any, RevRegDefResult]

    Returns:

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    issuer_id = body.get("issuerId")
    cred_def_id = body.get("credDefId")
    max_cred_num = body.get("maxCredNum")
    options = body.get("options")

    issuer = AnonCredsIssuer(context.profile)
    # check we published this cred def
    found = await issuer.match_created_credential_definitions(cred_def_id)
    if not found:
        raise web.HTTPNotFound(
            reason=f"Not issuer of credential definition id {cred_def_id}"
        )

    try:
        revoc = AnonCredsRevocation(context.profile)
        issuer_rev_reg_rec = await revoc.init_issuer_registry(
            issuer_id,
            cred_def_id,
            max_cred_num=max_cred_num,
            options=options,
            notify=False,
        )
    except RevocationNotSupportedError as e:
        raise web.HTTPBadRequest(reason=e.message) from e
    result = await shield(issuer_rev_reg_rec.create_and_register_def(context.profile))

    return web.json_response(result.serialize())


class RevListCreateRequestSchema(OpenAPISchema):
    """Request schema for revocation registry creation request."""

    rev_reg_def_id = fields.Str(
        description="Revocation registry definition identifier",
        data_key="revRegDefId",
    )


@docs(tags=["anoncreds"], summary="")
@request_schema(RevListCreateRequestSchema())
@response_schema(RevListResultSchema(), 200, description="")
async def rev_list_post(request: web.BaseRequest):
    """Request handler for creating .

    Args:


    (method) def create_and_register_revocation_registry_definition(
        issuer_id: str,
        cred_def_id: str,
        tag: str,
        max_cred_num: int,
        registry_type: str,
        tails_base_path: str,
        options: dict[Unknown, Unknown] | None = None
    ) -> Coroutine[Any, Any, RevRegDefResult]

    Returns:

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    rev_reg_def_id = body.get("revRegDefId")
    options = body.get("options")

    try:
        revoc = AnonCredsRevocation(context.profile)
        rev_reg = await revoc.get_issuer_rev_reg_record(rev_reg_def_id)
        result = await rev_reg.create_and_register_list(
            context.profile,
            options,
        )
        LOGGER.debug("published revocation list for: %s", rev_reg_def_id)

    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except AnonCredsIssuerError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(result.serialize())


@docs(
    tags=["revocation"],
    summary="Upload local tails file to server",
)
@match_info_schema(RevRegIdMatchInfoSchema())
@response_schema(RevocationModuleResponseSchema(), description="")
async def upload_tails_file(request: web.BaseRequest):
    """
    Request handler to upload local tails file for revocation registry.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    profile: AskarProfile = context.profile
    anoncreds_registry: AnonCredsRegistry = context.inject(AnonCredsRegistry)
    rev_reg_id = request.match_info["rev_reg_id"]
    try:
        issuer = AnonCredsIssuer(profile)
        get_rev_reg_def: GetRevRegDefResult = (
            await anoncreds_registry.get_revocation_registry_definition(
                profile, rev_reg_id
            )
        )
        rev_reg_def: RevRegDef = get_rev_reg_def.revocation_registry
    # TODO: Should we check if tails file exists
    except StorageNotFoundError as err:  # TODO: update error
        raise web.HTTPNotFound(reason=err.roll_up) from err
    try:
        await issuer.upload_tails_file(rev_reg_def)
    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e

    return web.json_response({})


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
                "/anoncreds/credential-definitions",
                cred_defs_get,
                allow_head=False,
            ),
            web.post("/anoncreds/revocation-registry-definition", rev_reg_def_post),
            web.post("/anoncreds/revocation-list", rev_list_post),
            web.put("/anoncreds/registry/{rev_reg_id}/tails-file", upload_tails_file),
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
