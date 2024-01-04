"""Anoncreds admin routes."""
import logging
from asyncio import shield

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)
from marshmallow import fields

from aries_cloudagent.ledger.error import LedgerError

from ..admin.request_context import AdminRequestContext
from ..askar.profile import AskarProfile
from ..core.event_bus import EventBus
from ..messaging.models.openapi import OpenAPISchema
from ..messaging.valid import (
    INDY_CRED_DEF_ID_EXAMPLE,
    INDY_OR_KEY_DID_EXAMPLE,
    INDY_REV_REG_ID_EXAMPLE,
    INDY_SCHEMA_ID_EXAMPLE,
    UUIDFour,
)
from ..revocation.error import RevocationError, RevocationNotSupportedError
from ..revocation_anoncreds.manager import RevocationManager, RevocationManagerError
from ..revocation_anoncreds.routes import (
    PublishRevocationsSchema,
    RevocationModuleResponseSchema,
    RevokeRequestSchema,
    RevRegIdMatchInfoSchema,
    TxnOrPublishRevocationsResultSchema,
)
from ..storage.error import StorageError, StorageNotFoundError
from .base import (
    AnonCredsObjectNotFound,
    AnonCredsRegistrationError,
    AnonCredsResolutionError,
)
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

    schema_id = fields.Str(
        description="Schema identifier",
        example=INDY_SCHEMA_ID_EXAMPLE,
    )


class CredIdMatchInfo(OpenAPISchema):
    """Path parameters and validators for request taking credential id."""

    cred_def_id = fields.Str(
        description="Credential identifier",
        required=True,
        example=INDY_CRED_DEF_ID_EXAMPLE,
    )


class InnerCredDefSchema(OpenAPISchema):
    """Parameters and validators for credential definition."""

    tag = fields.Str(description="Credential definition tag", example="default")
    schema_id = fields.Str(
        description="Schema identifier",
        data_key="schemaId",
        example=INDY_SCHEMA_ID_EXAMPLE,
    )
    issuer_id = fields.Str(
        data_key="issuerId",
        example=INDY_OR_KEY_DID_EXAMPLE,
    )


class CredDefPostOptionsSchema(OpenAPISchema):
    """Parameters and validators for credential definition options."""

    endorser_connection_id = fields.Str(required=False, example=UUIDFour.EXAMPLE)
    support_revocation = fields.Bool(required=False)
    revocation_registry_size = fields.Int(required=False, example=666)


class CredDefPostRequestSchema(OpenAPISchema):
    """Parameters and validators for query string in create credential definition."""

    credential_definition = fields.Nested(InnerCredDefSchema())
    options = fields.Nested(CredDefPostOptionsSchema())


class CredDefsQueryStringSchema(OpenAPISchema):
    """Parameters and validators for credential definition list query."""

    issuer_id = fields.Str(
        description="Issuer Identifier of the credential definition",
        example=INDY_OR_KEY_DID_EXAMPLE,
    )
    schema_id = fields.Str(
        description="Schema identifier",
        example=INDY_SCHEMA_ID_EXAMPLE,
    )
    schema_name = fields.Str(description="Schema name", example="Example schema")
    schema_version = fields.Str(description="Schema version", example="1.0")


class SchemaPostOptionSchema(OpenAPISchema):
    """Parameters and validators for schema options."""

    endorser_connection_id = fields.Str(
        description="Connection identifier (optional) (this is an example)",
        required=False,
        example=UUIDFour.EXAMPLE,
    )


class SchemaPostRequestSchema(OpenAPISchema):
    """Parameters and validators for query string in create schema."""

    schema = fields.Nested(AnonCredsSchemaSchema())
    options = fields.Nested(SchemaPostOptionSchema())


@docs(tags=["anoncreds"], summary="Create a schema on the connected ledger")
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
    options = body.get("options")
    schema_data = body.get("schema")

    if schema_data is None:
        raise web.HTTPBadRequest(reason="schema object is required")

    issuer_id = schema_data.get("issuerId")
    attr_names = schema_data.get("attrNames")
    name = schema_data.get("name")
    version = schema_data.get("version")

    issuer = AnonCredsIssuer(context.profile)
    try:
        result = await issuer.create_and_register_schema(
            issuer_id, name, version, attr_names, options=options
        )
        return web.json_response(result.serialize())
    except (AnonCredsIssuerError, AnonCredsRegistrationError) as e:
        raise web.HTTPBadRequest(reason=e.roll_up) from e


@docs(tags=["anoncreds"], summary="Retrieve an individual schemas details")
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
    schema_id = request.match_info["schema_id"]
    try:
        schema = await anoncreds_registry.get_schema(context.profile, schema_id)
        return web.json_response(schema.serialize())
    except AnonCredsObjectNotFound:
        raise web.HTTPNotFound(reason=f"Schema not found: {schema_id}")
    except AnonCredsResolutionError as e:
        raise web.HTTPBadRequest(reason=e.roll_up)


class SchemasQueryStringSchema(OpenAPISchema):
    """Parameters and validators for query string in schemas list query."""

    schema_name = fields.Str(description="Schema name", example="example-schema")
    schema_version = fields.Str(description="Schema version", example="1.0")
    schema_issuer_id = fields.Str(
        description="Issuer identifier of the schema",
        example=INDY_OR_KEY_DID_EXAMPLE,
    )


class GetSchemasResponseSchema(OpenAPISchema):
    """Parameters and validators for schema list all response."""

    schema_ids = fields.List(
        fields.Str(description="Schema identifier", example=INDY_SCHEMA_ID_EXAMPLE)
    )


@docs(tags=["anoncreds"], summary="Retrieve all schema ids")
@querystring_schema(SchemasQueryStringSchema())
@response_schema(GetSchemasResponseSchema(), 200, description="")
async def schemas_get(request: web.BaseRequest):
    """Request handler for getting all schemas.

    Args:
        request: aiohttp request object

    Returns:
        The credential definition details.

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


@docs(
    tags=["anoncreds"], summary="Create a credential definition on the connected ledger"
)
@request_schema(CredDefPostRequestSchema())
@response_schema(CredDefResultSchema(), 200, description="")
async def cred_def_post(request: web.BaseRequest):
    """Request handler for creating .

    Args:
        request: aiohttp request object

    Returns:
        The credential definition details.

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    options = body.get("options")
    cred_def = body.get("credential_definition")

    if cred_def is None:
        raise web.HTTPBadRequest(reason="cred_def object is required")

    issuer_id = cred_def.get("issuerId")
    schema_id = cred_def.get("schemaId")
    tag = cred_def.get("tag")

    issuer = AnonCredsIssuer(context.profile)
    try:
        result = await issuer.create_and_register_credential_definition(
            issuer_id,
            schema_id,
            tag,
            options=options,
        )
        return web.json_response(result.serialize())
    except (
        AnonCredsObjectNotFound,
        AnonCredsResolutionError,
        ValueError,
    ) as e:
        raise web.HTTPBadRequest(reason=e.roll_up)
    except AnonCredsIssuerError as e:
        raise web.HTTPServerError(reason=e.roll_up)


@docs(
    tags=["anoncreds"], summary="Retrieve an individual credential definition details"
)
@match_info_schema(CredIdMatchInfo())
@response_schema(GetCredDefResultSchema(), 200, description="")
async def cred_def_get(request: web.BaseRequest):
    """Request handler for getting credential definition.

    Args:
        request: aiohttp request object

    Returns:
        The credential definition details.

    """
    context: AdminRequestContext = request["context"]
    anon_creds_registry = context.inject(AnonCredsRegistry)
    credential_id = request.match_info["cred_def_id"]
    try:
        result = await anon_creds_registry.get_credential_definition(
            context.profile, credential_id
        )
        return web.json_response(result.serialize())
    except AnonCredsObjectNotFound:
        raise web.HTTPBadRequest(
            reason=f"Credential definition {credential_id} not found"
        )


class GetCredDefsResponseSchema(OpenAPISchema):
    """AnonCredsRegistryGetCredDefsSchema."""

    credential_definition_ids = fields.List(
        fields.Str(
            description="credential definition identifiers",
            example="GvLGiRogTJubmj5B36qhYz:3:CL:8:faber.agent.degree_schema",
        )
    )


@docs(tags=["anoncreds"], summary="Retrieve all credential definition ids")
@querystring_schema(CredDefsQueryStringSchema())
@response_schema(GetCredDefsResponseSchema(), 200, description="")
async def cred_defs_get(request: web.BaseRequest):
    """Request handler for getting all credential definitions.

    Args:
        request: aiohttp request object

    Returns:
        The credential definition details.

    """
    context: AdminRequestContext = request["context"]
    issuer = AnonCredsIssuer(context.profile)

    cred_def_ids = await issuer.get_created_credential_definitions(
        issuer_id=request.query.get("issuer_id"),
        schema_id=request.query.get("schema_id"),
        schema_name=request.query.get("schema_name"),
        schema_version=request.query.get("schema_version"),
    )
    return web.json_response({"credential_definition_ids": cred_def_ids})


class InnerRevRegDefSchema(OpenAPISchema):
    """Request schema for revocation registry creation request."""

    issuer_id = fields.Str(
        description="Issuer Identifier of the credential definition or schema",
        data_key="issuerId",
        example=INDY_OR_KEY_DID_EXAMPLE,
    )
    cred_def_id = fields.Str(
        description="Credential definition identifier",
        data_key="credDefId",
        example=INDY_SCHEMA_ID_EXAMPLE,
    )
    tag = fields.Str(description="tag for revocation registry", example="default")
    max_cred_num = fields.Int(
        description="Maximum number of credential revocations per registry",
        data_key="maxCredNum",
        example=666,
    )


class RevRegDefOptionsSchema(OpenAPISchema):
    """Parameters and validators for rev reg def options."""

    endorser_connection_id = fields.Str(
        description="Connection identifier (optional) (this is an example)",
        required=False,
        example=UUIDFour.EXAMPLE,
    )


class RevRegCreateRequestSchema(OpenAPISchema):
    """Wrapper for revocation registry creation request."""

    revocation_registry_definition = fields.Nested(InnerRevRegDefSchema())
    options = fields.Nested(RevRegDefOptionsSchema())


@docs(
    tags=["anoncreds"],
    summary="Create and publish a registration revocation on the connected ledger",
)
@request_schema(RevRegCreateRequestSchema())
@response_schema(RevRegDefResultSchema(), 200, description="")
async def rev_reg_def_post(request: web.BaseRequest):
    """Request handler for creating revocation registry definition."""
    context: AdminRequestContext = request["context"]
    body = await request.json()

    revocation_registry_definition = body.get("revocation_registry_definition")
    options = body.get("options")

    if revocation_registry_definition is None:
        raise web.HTTPBadRequest(
            reason="revocation_registry_definition object is required"
        )

    issuer_id = revocation_registry_definition.get("issuerId")
    cred_def_id = revocation_registry_definition.get("credDefId")
    max_cred_num = revocation_registry_definition.get("maxCredNum")

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
        return web.json_response(result.serialize())
    except (RevocationNotSupportedError, AnonCredsRevocationError) as e:
        raise web.HTTPBadRequest(reason=e.roll_up) from e


class RevListCreateRequestSchema(OpenAPISchema):
    """Request schema for revocation registry creation request."""

    rev_reg_def_id = fields.Str(
        description="Revocation registry definition identifier",
        example=INDY_REV_REG_ID_EXAMPLE,
    )


@docs(
    tags=["anoncreds"],
    summary="Create and publish a revocation status list on the connected ledger",
)
@request_schema(RevListCreateRequestSchema())
@response_schema(RevListResultSchema(), 200, description="")
async def rev_list_post(request: web.BaseRequest):
    """Request handler for creating registering a revocation list."""
    context: AdminRequestContext = request["context"]
    body = await request.json()
    rev_reg_def_id = body.get("rev_reg_def_id")
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
        return web.json_response(result.serialize())
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (AnonCredsRevocationError, LedgerError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err


@docs(
    tags=["anoncreds"],
    summary="Upload local tails file to server",
)
@match_info_schema(RevRegIdMatchInfoSchema())
@response_schema(RevocationModuleResponseSchema(), description="")
async def upload_tails_file(request: web.BaseRequest):
    """Request handler to upload local tails file for revocation registry.

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
        return web.json_response({})
    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e


@docs(
    tags=["anoncreds"],
    summary="Update the active registry",
)
@match_info_schema(RevRegIdMatchInfoSchema())
@response_schema(RevocationModuleResponseSchema(), description="")
async def set_active_registry(request: web.BaseRequest):
    """Request handler to set the active registry.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    rev_reg_id = request.match_info["rev_reg_id"]
    try:
        revocation = AnonCredsRevocation(context.profile)
        await revocation.set_active_registry(rev_reg_id)
        return web.json_response({})
    except AnonCredsRevocationError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e


@docs(
    tags=["anoncreds"],
    summary="Revoke an issued credential",
)
@request_schema(RevokeRequestSchema())
@response_schema(RevocationModuleResponseSchema(), description="")
async def revoke(request: web.BaseRequest):
    """Request handler for storing a credential revocation.

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
        return web.json_response({})
    except (
        RevocationManagerError,
        AnonCredsRevocationError,
        StorageError,
        AnonCredsIssuerError,
        AnonCredsRegistrationError,
    ) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err


@docs(tags=["revocation"], summary="Publish pending revocations to ledger")
@request_schema(PublishRevocationsSchema())
@response_schema(TxnOrPublishRevocationsResultSchema(), 200, description="")
async def publish_revocations(request: web.BaseRequest):
    """Request handler for publishing pending revocations to the ledger.

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
        return web.json_response({"rrid2crid": rev_reg_resp})
    except (
        RevocationError,
        StorageError,
        AnonCredsIssuerError,
        AnonCredsRevocationError,
    ) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/anoncreds/schema", schemas_post),
            web.get("/anoncreds/schema/{schema_id}", schema_get, allow_head=False),
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
