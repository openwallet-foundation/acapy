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

from ..admin.request_context import AdminRequestContext
from ..askar.profile import AskarProfile
from ..core.event_bus import EventBus
from ..messaging.models.openapi import OpenAPISchema
from ..messaging.valid import UUIDFour
from ..revocation.error import RevocationError, RevocationNotSupportedError
from ..revocation.manager import RevocationManager, RevocationManagerError
from ..revocation.routes import (
    PublishRevocationsSchema,
    RevRegIdMatchInfoSchema,
    RevocationModuleResponseSchema,
    RevokeRequestSchema,
    TxnOrPublishRevocationsResultSchema,
)
from ..storage.error import StorageError, StorageNotFoundError
from .base import AnonCredsRegistrationError
from .issuer import AnonCredsIssuer, AnonCredsIssuerError
from .models.anoncreds_cred_def import CredDefResultSchema, GetCredDefResultSchema
from .models.anoncreds_revocation import RevListResultSchema, RevRegDefResultSchema
from .models.anoncreds_schema import (
    AnonCredsSchemaSchema,
    GetSchemaResultSchema,
    SchemaResultSchema,
)
from .registry import AnonCredsRegistry
from .revocation import AnonCredsRevocation, AnonCredsRevocationError
from .revocation_setup import DefaultRevocationSetup

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
    """AnonCredsRegistryGetCredDefsSchema."""

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
    """Request handler for creating revocation registry definition."""
    context: AdminRequestContext = request["context"]
    body = await request.json()
    issuer_id = body.get("issuerId")
    cred_def_id = body.get("credDefId")
    max_cred_num = body.get("maxCredNum")
    options = body.get("options")

    issuer = AnonCredsIssuer(context.profile)
    revocation = AnonCredsRevocation(context.profile)
    # check we published this cred def
    found = await issuer.match_created_credential_definitions(cred_def_id)
    if not found:
        raise web.HTTPNotFound(
            reason=f"Not issuer of credential definition id {cred_def_id}"
        )

    try:
        result = await shield(
            revocation.create_and_register_revocation_registry_definition(
                issuer_id,
                cred_def_id,
                registry_type="CL_ACCUM",
                max_cred_num=max_cred_num,
                tag="default",
                options=options,
            )
        )
    except RevocationNotSupportedError as e:
        raise web.HTTPBadRequest(reason=e.message) from e
    except AnonCredsRevocationError as e:
        raise web.HTTPBadRequest(reason=e.message) from e

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
    """Request handler for creating registering a revocation list."""
    context: AdminRequestContext = request["context"]
    body = await request.json()
    rev_reg_def_id = body.get("revRegDefId")
    options = body.get("options")

    revocation = AnonCredsRevocation(context.profile)
    try:
        result = await shield(
            revocation.create_and_register_revocation_list(
                rev_reg_def_id,
                options,
            )
        )
        LOGGER.debug("published revocation list for: %s", rev_reg_def_id)

    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except AnonCredsRevocationError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(result.serialize())


@docs(
    tags=["anoncreds"],
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
    rev_reg_id = request.match_info["rev_reg_id"]
    try:
        revocation = AnonCredsRevocation(profile)
        rev_reg_def = await revocation.get_created_revocation_registry_definition(
            rev_reg_id
        )
        if rev_reg_def is None:
            raise web.HTTPNotFound(reason="No rev reg def found")

        await revocation.upload_tails_file(rev_reg_def)

    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e

    return web.json_response({})


@docs(
    tags=["anoncreds"],
    summary="Upload local tails file to server",
)
@match_info_schema(RevRegIdMatchInfoSchema())
@response_schema(RevocationModuleResponseSchema(), description="")
async def set_active_registry(request: web.BaseRequest):
    """
    Request handler to upload local tails file for revocation registry.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    rev_reg_id = request.match_info["rev_reg_id"]
    try:
        revocation = AnonCredsRevocation(context.profile)
        await revocation.set_active_registry(rev_reg_id)
    except AnonCredsRevocationError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e

    return web.json_response({})


@docs(
    tags=["anoncreds"],
    summary="Revoke an issued credential",
)
@request_schema(RevokeRequestSchema())
@response_schema(RevocationModuleResponseSchema(), description="")
async def revoke(request: web.BaseRequest):
    """
    Request handler for storing a credential revocation.

    Args:
        request: aiohttp request object

    Returns:
        The credential revocation details.

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    cred_ex_id = body.get("cred_ex_id")
    body["notify"] = body.get("notify", context.settings.get("revocation.notify"))
    notify = body.get("notify")
    connection_id = body.get("connection_id")
    body["notify_version"] = body.get("notify_version", "v1_0")
    notify_version = body["notify_version"]

    if notify and not connection_id:
        raise web.HTTPBadRequest(reason="connection_id must be set when notify is true")
    if notify and not notify_version:
        raise web.HTTPBadRequest(
            reason="Request must specify notify_version if notify is true"
        )

    rev_manager = RevocationManager(context.profile)
    try:
        if cred_ex_id:
            # rev_reg_id and cred_rev_id should not be present so we can
            # safely splat the body
            await rev_manager.revoke_credential_by_cred_ex_id(**body)
        else:
            # no cred_ex_id so we can safely splat the body
            await rev_manager.revoke_credential(**body)
    except (
        RevocationManagerError,
        AnonCredsRevocationError,
        StorageError,
        AnonCredsIssuerError,
        AnonCredsRegistrationError,
    ) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


@docs(tags=["revocation"], summary="Publish pending revocations to ledger")
@request_schema(PublishRevocationsSchema())
@response_schema(TxnOrPublishRevocationsResultSchema(), 200, description="")
async def publish_revocations(request: web.BaseRequest):
    """
    Request handler for publishing pending revocations to the ledger.

    Args:
        request: aiohttp request object

    Returns:
        Credential revocation ids published as revoked by revocation registry id.

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    rrid2crid = body.get("rrid2crid")

    rev_manager = RevocationManager(context.profile)

    try:
        rev_reg_resp = await rev_manager.publish_pending_revocations(
            rrid2crid,
        )
    except (
        RevocationError,
        StorageError,
        AnonCredsIssuerError,
        AnonCredsRevocationError,
    ) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"rrid2crid": rev_reg_resp})


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
            web.put("/anoncreds/registry/{rev_reg_id}/active", set_active_registry),
            web.post("/anoncreds/revoke", revoke),
            web.post("/anoncreds/publish-revocations", publish_revocations),
        ]
    )


def register_events(event_bus: EventBus):
    """Register events."""
    # TODO Make this pluggable?
    setup_manager = DefaultRevocationSetup()
    setup_manager.register_events(event_bus)


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
