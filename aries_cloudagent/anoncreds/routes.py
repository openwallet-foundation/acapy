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

from ..admin.request_context import AdminRequestContext
from ..core.event_bus import EventBus
from ..ledger.error import LedgerError
from ..messaging.models.openapi import OpenAPISchema
from ..messaging.valid import (
    INDY_CRED_DEF_ID_EXAMPLE,
    INDY_OR_KEY_DID_EXAMPLE,
    INDY_REV_REG_ID_EXAMPLE,
    INDY_SCHEMA_ID_EXAMPLE,
    UUIDFour,
)
from ..revocation.error import RevocationNotSupportedError
from ..revocation.routes import (
    RevocationModuleResponseSchema,
    RevRegIdMatchInfoSchema,
)
from ..storage.error import StorageNotFoundError
from ..utils.profiles import is_not_anoncreds_profile_raise_web_exception
from .base import (
    AnonCredsObjectNotFound,
    AnonCredsRegistrationError,
    AnonCredsResolutionError,
)
from .issuer import AnonCredsIssuer, AnonCredsIssuerError
from .models.anoncreds_cred_def import (
    CredDefResultSchema,
    GetCredDefResultSchema,
)
from .models.anoncreds_revocation import RevListResultSchema, RevRegDefResultSchema
from .models.anoncreds_schema import (
    AnonCredsSchemaSchema,
    GetSchemaResultSchema,
    SchemaResultSchema,
)
from .registry import AnonCredsRegistry
from .revocation import AnonCredsRevocation, AnonCredsRevocationError
from .revocation_setup import DefaultRevocationSetup
from .util import handle_value_error

LOGGER = logging.getLogger(__name__)

SPEC_URI = "https://hyperledger.github.io/anoncreds-spec"

endorser_connection_id_description = (
    "Connection identifier (optional) (this is an example). "
    "You can set this if you know the endorser's connection id you want to use. "
    "If not specified then the agent will attempt to find an endorser connection."
)
create_transaction_for_endorser_description = (
    "Create transaction for endorser (optional, default false). "
    "Use this for agents who don't specify an author role but want to "
    "create a transaction for an endorser to sign."
)


class SchemaIdMatchInfo(OpenAPISchema):
    """Path parameters and validators for request taking schema id."""

    schema_id = fields.Str(
        metadata={
            "description": "Schema identifier",
            "example": INDY_SCHEMA_ID_EXAMPLE,
        }
    )


class SchemaPostOptionSchema(OpenAPISchema):
    """Parameters and validators for schema options."""

    endorser_connection_id = fields.Str(
        metadata={
            "description": endorser_connection_id_description,
            "example": UUIDFour.EXAMPLE,
        },
        required=False,
    )

    create_transaction_for_endorser = fields.Bool(
        metadata={
            "description": create_transaction_for_endorser_description,
            "example": False,
        },
        required=False,
    )


class SchemasQueryStringSchema(OpenAPISchema):
    """Parameters and validators for query string in schemas list query."""

    schema_name = fields.Str(
        metadata={
            "description": "Schema name",
            "example": "example-schema",
        }
    )
    schema_version = fields.Str(
        metadata={
            "description": "Schema version",
            "example": "1.0",
        }
    )
    schema_issuer_id = fields.Str(
        metadata={
            "description": "Schema issuer identifier",
            "example": INDY_OR_KEY_DID_EXAMPLE,
        }
    )


class GetSchemasResponseSchema(OpenAPISchema):
    """Parameters and validators for schema list all response."""

    schema_ids = fields.List(
        fields.Str(
            metadata={
                "description": "Schema identifiers",
                "example": INDY_SCHEMA_ID_EXAMPLE,
            }
        )
    )


class SchemaPostRequestSchema(OpenAPISchema):
    """Parameters and validators for query string in create schema."""

    schema = fields.Nested(AnonCredsSchemaSchema())
    options = fields.Nested(SchemaPostOptionSchema())


@docs(tags=["anoncreds - schemas"], summary="Create a schema on the connected ledger")
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
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    body = await request.json()
    options = body.get("options", {})
    schema_data = body.get("schema")

    if schema_data is None:
        raise web.HTTPBadRequest(reason="schema object is required")

    issuer_id = schema_data.get("issuerId")
    attr_names = schema_data.get("attrNames")
    name = schema_data.get("name")
    version = schema_data.get("version")

    try:
        issuer = AnonCredsIssuer(profile)
        result = await issuer.create_and_register_schema(
            issuer_id,
            name,
            version,
            attr_names,
            options,
        )
        return web.json_response(result.serialize())
    except ValueError as e:
        handle_value_error(e)
    except (AnonCredsIssuerError, AnonCredsRegistrationError) as e:
        raise web.HTTPBadRequest(reason=e.roll_up) from e


@docs(tags=["anoncreds - schemas"], summary="Retrieve an individual schemas details")
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
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    anoncreds_registry = context.inject(AnonCredsRegistry)
    schema_id = request.match_info["schema_id"]
    try:
        schema = await anoncreds_registry.get_schema(profile, schema_id)
        return web.json_response(schema.serialize())
    except AnonCredsObjectNotFound as e:
        raise web.HTTPNotFound(reason=f"Schema not found: {schema_id}") from e
    except AnonCredsResolutionError as e:
        raise web.HTTPBadRequest(reason=e.roll_up) from e


@docs(tags=["anoncreds - schemas"], summary="Retrieve all schema ids")
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
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    schema_issuer_id = request.query.get("schema_issuer_id")
    schema_name = request.query.get("schema_name")
    schema_version = request.query.get("schema_version")

    try:
        issuer = AnonCredsIssuer(profile)
        schema_ids = await issuer.get_created_schemas(
            schema_name, schema_version, schema_issuer_id
        )
    except ValueError as e:
        handle_value_error(e)
    return web.json_response({"schema_ids": schema_ids})


class CredIdMatchInfo(OpenAPISchema):
    """Path parameters and validators for request taking credential id."""

    cred_def_id = fields.Str(
        metadata={
            "description": "Credential definition identifier",
            "example": INDY_CRED_DEF_ID_EXAMPLE,
        },
        required=True,
    )


class InnerCredDefSchema(OpenAPISchema):
    """Parameters and validators for credential definition."""

    tag = fields.Str(
        metadata={
            "description": "Credential definition tag",
            "example": "default",
        },
        required=True,
    )
    schema_id = fields.Str(
        metadata={
            "description": "Schema identifier",
            "example": INDY_SCHEMA_ID_EXAMPLE,
        },
        required=True,
        data_key="schemaId",
    )
    issuer_id = fields.Str(
        metadata={
            "description": "Issuer Identifier of the credential definition",
            "example": INDY_OR_KEY_DID_EXAMPLE,
        },
        required=True,
        data_key="issuerId",
    )


class CredDefPostOptionsSchema(OpenAPISchema):
    """Parameters and validators for credential definition options."""

    endorser_connection_id = fields.Str(
        metadata={
            "description": endorser_connection_id_description,
            "example": UUIDFour.EXAMPLE,
        },
        required=False,
    )
    create_transaction_for_endorser = fields.Bool(
        metadata={
            "description": create_transaction_for_endorser_description,
            "example": False,
        },
        required=False,
    )
    support_revocation = fields.Bool(
        metadata={
            "description": "Support credential revocation",
        },
        required=False,
    )
    revocation_registry_size = fields.Int(
        metadata={
            "description": "Maximum number of credential revocations per registry",
            "example": 1000,
        },
        required=False,
    )


class CredDefPostRequestSchema(OpenAPISchema):
    """Parameters and validators for query string in create credential definition."""

    credential_definition = fields.Nested(InnerCredDefSchema())
    options = fields.Nested(CredDefPostOptionsSchema())


class CredDefsQueryStringSchema(OpenAPISchema):
    """Parameters and validators for credential definition list query."""

    issuer_id = fields.Str(
        metadata={
            "description": "Issuer Identifier of the credential definition",
            "example": INDY_OR_KEY_DID_EXAMPLE,
        }
    )
    schema_id = fields.Str(
        metadata={
            "description": "Schema identifier",
            "example": INDY_SCHEMA_ID_EXAMPLE,
        }
    )
    schema_name = fields.Str(
        metadata={
            "description": "Schema name",
            "example": "example-schema",
        }
    )
    schema_version = fields.Str(
        metadata={
            "description": "Schema version",
            "example": "1.0",
        }
    )


@docs(
    tags=["anoncreds - credential definitions"],
    summary="Create a credential definition on the connected ledger",
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
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    body = await request.json()
    options = body.get("options", {})
    cred_def = body.get("credential_definition")

    if cred_def is None:
        raise web.HTTPBadRequest(reason="cred_def object is required")

    issuer_id = cred_def.get("issuerId")
    schema_id = cred_def.get("schemaId")
    tag = cred_def.get("tag")

    try:
        issuer = AnonCredsIssuer(profile)
        result = await issuer.create_and_register_credential_definition(
            issuer_id,
            schema_id,
            tag,
            options=options,
        )
        return web.json_response(result.serialize())
    except ValueError as e:
        handle_value_error(e)
    except (
        AnonCredsIssuerError,
        AnonCredsObjectNotFound,
        AnonCredsResolutionError,
    ) as e:
        raise web.HTTPBadRequest(reason=e.roll_up) from e


@docs(
    tags=["anoncreds - credential definitions"],
    summary="Retrieve an individual credential definition details",
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
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    anon_creds_registry = context.inject(AnonCredsRegistry)
    credential_id = request.match_info["cred_def_id"]
    try:
        result = await anon_creds_registry.get_credential_definition(
            profile, credential_id
        )
        return web.json_response(result.serialize())
    except AnonCredsObjectNotFound as e:
        raise web.HTTPBadRequest(
            reason=f"Credential definition {credential_id} not found"
        ) from e


class GetCredDefsResponseSchema(OpenAPISchema):
    """AnonCredsRegistryGetCredDefsSchema."""

    credential_definition_ids = fields.List(
        fields.Str(
            metadata={
                "description": "credential definition identifiers",
                "example": "GvLGiRogTJubmj5B36qhYz:3:CL:8:faber.agent.degree_schema",
            }
        )
    )


@docs(
    tags=["anoncreds - credential definitions"],
    summary="Retrieve all credential definition ids",
)
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
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    try:
        issuer = AnonCredsIssuer(profile)

        cred_def_ids = await issuer.get_created_credential_definitions(
            issuer_id=request.query.get("issuer_id"),
            schema_id=request.query.get("schema_id"),
            schema_name=request.query.get("schema_name"),
            schema_version=request.query.get("schema_version"),
        )
        return web.json_response({"credential_definition_ids": cred_def_ids})
    except ValueError as e:
        handle_value_error(e)


class InnerRevRegDefSchema(OpenAPISchema):
    """Request schema for revocation registry creation request."""

    issuer_id = fields.Str(
        metadata={
            "description": "Issuer Identifier of the credential definition or schema",
            "example": INDY_OR_KEY_DID_EXAMPLE,
        },
        data_key="issuerId",
    )
    cred_def_id = fields.Str(
        metadata={
            "description": "Credential definition identifier",
            "example": INDY_SCHEMA_ID_EXAMPLE,
        },
        data_key="credDefId",
    )
    tag = fields.Str(
        metadata={"description": "tag for revocation registry", "example": "default"}
    )
    max_cred_num = fields.Int(
        metadata={
            "description": "Maximum number of credential revocations per registry",
            "example": 777,
        },
        data_key="maxCredNum",
    )


class RevRegDefOptionsSchema(OpenAPISchema):
    """Parameters and validators for rev reg def options."""

    endorser_connection_id = fields.Str(
        metadata={
            "description": endorser_connection_id_description,
            "example": UUIDFour.EXAMPLE,
        },
        required=False,
    )
    create_transaction_for_endorser = fields.Bool(
        metadata={
            "description": create_transaction_for_endorser_description,
            "example": False,
        },
        required=False,
    )


class RevRegCreateRequestSchemaAnoncreds(OpenAPISchema):
    """Wrapper for revocation registry creation request."""

    revocation_registry_definition = fields.Nested(InnerRevRegDefSchema())
    options = fields.Nested(RevRegDefOptionsSchema())


@docs(
    tags=["anoncreds - revocation"],
    summary="Create and publish a registration revocation on the connected ledger",
)
@request_schema(RevRegCreateRequestSchemaAnoncreds())
@response_schema(RevRegDefResultSchema(), 200, description="")
async def rev_reg_def_post(request: web.BaseRequest):
    """Request handler for creating revocation registry definition."""
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    body = await request.json()
    revocation_registry_definition = body.get("revocation_registry_definition")
    options = body.get("options", {})

    if revocation_registry_definition is None:
        raise web.HTTPBadRequest(
            reason="revocation_registry_definition object is required"
        )

    issuer_id = revocation_registry_definition.get("issuerId")
    cred_def_id = revocation_registry_definition.get("credDefId")
    max_cred_num = revocation_registry_definition.get("maxCredNum")
    tag = revocation_registry_definition.get("tag")

    issuer = AnonCredsIssuer(profile)
    revocation = AnonCredsRevocation(profile)
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
                tag=tag,
                options=options,
            )
        )
        return web.json_response(result.serialize())
    except (RevocationNotSupportedError, AnonCredsRevocationError) as e:
        raise web.HTTPBadRequest(reason=e.roll_up) from e


class RevListOptionsSchema(OpenAPISchema):
    """Parameters and validators for revocation list options."""

    endorser_connection_id = fields.Str(
        metadata={
            "description": endorser_connection_id_description,
            "example": UUIDFour.EXAMPLE,
        },
        required=False,
    )
    create_transaction_for_endorser = fields.Bool(
        metadata={
            "description": create_transaction_for_endorser_description,
            "example": False,
        },
        required=False,
    )


class RevListCreateRequestSchema(OpenAPISchema):
    """Request schema for revocation registry creation request."""

    rev_reg_def_id = fields.Str(
        metadata={
            "description": "Revocation registry definition identifier",
            "example": INDY_REV_REG_ID_EXAMPLE,
        }
    )
    options = fields.Nested(RevListOptionsSchema)


@docs(
    tags=["anoncreds - revocation"],
    summary="Create and publish a revocation status list on the connected ledger",
)
@request_schema(RevListCreateRequestSchema())
@response_schema(RevListResultSchema(), 200, description="")
async def rev_list_post(request: web.BaseRequest):
    """Request handler for creating registering a revocation list."""
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    body = await request.json()
    rev_reg_def_id = body.get("rev_reg_def_id")
    options = body.get("options", {})

    try:
        revocation = AnonCredsRevocation(profile)
        result = await shield(
            revocation.create_and_register_revocation_list(
                rev_reg_def_id,
                options,
            )
        )
        LOGGER.debug("published revocation list for: %s", rev_reg_def_id)
        return web.json_response(result.serialize())
    except ValueError as e:
        handle_value_error(e)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (AnonCredsRevocationError, LedgerError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err


@docs(
    tags=["anoncreds - revocation"],
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
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

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
    except ValueError as e:
        handle_value_error(e)
    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e


@docs(
    tags=["anoncreds - revocation"],
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
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    rev_reg_id = request.match_info["rev_reg_id"]
    try:
        revocation = AnonCredsRevocation(profile)
        await revocation.set_active_registry(rev_reg_id)
        return web.json_response({})
    except ValueError as e:
        handle_value_error(e)
    except AnonCredsRevocationError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e


def register_events(event_bus: EventBus):
    """Register events."""
    # TODO Make this pluggable?
    setup_manager = DefaultRevocationSetup()
    setup_manager.register_events(event_bus)


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
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "anoncreds - schemas",
            "description": "Anoncreds schema management",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "anoncreds - credential definitions",
            "description": "Anoncreds credential definition management",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
