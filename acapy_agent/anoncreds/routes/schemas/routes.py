"""AnonCreds schema routes."""

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)

from ....admin.decorators.auth import tenant_authentication
from ....admin.request_context import AdminRequestContext
from ....utils.profiles import is_not_anoncreds_profile_raise_web_exception
from ...base import (
    AnonCredsObjectNotFound,
    AnonCredsRegistrationError,
    AnonCredsResolutionError,
)
from ...issuer import AnonCredsIssuer, AnonCredsIssuerError
from ...models.schema import (
    GetSchemaResultSchema,
    SchemaResultSchema,
)
from ...registry import AnonCredsRegistry
from ...util import handle_value_error
from ..common.utils import get_request_body_with_profile_check
from .models import (
    GetSchemasResponseSchema,
    SchemaIdMatchInfo,
    SchemaPostRequestSchema,
    SchemasQueryStringSchema,
)

SCHEMAS_TAG_TITLE = "AnonCreds - Schemas"
SPEC_URI = "https://hyperledger.github.io/anoncreds-spec"


@docs(
    tags=[SCHEMAS_TAG_TITLE],
    summary="Create a schema on the connected datastore",
)
@request_schema(SchemaPostRequestSchema())
@response_schema(SchemaResultSchema(), 200, description="")
@tenant_authentication
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
            registration_metadata : This field contains metadata about the registration
            process
            schema_metadata : This fields contains metadata about the schema.

    """
    _, profile, body, options = await get_request_body_with_profile_check(request)
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


@docs(
    tags=[SCHEMAS_TAG_TITLE],
    summary="Retrieve an individual schemas details",
)
@match_info_schema(SchemaIdMatchInfo())
@response_schema(GetSchemaResultSchema(), 200, description="")
@tenant_authentication
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


@docs(
    tags=[SCHEMAS_TAG_TITLE],
    summary="Retrieve all schema ids",
)
@querystring_schema(SchemasQueryStringSchema())
@response_schema(GetSchemasResponseSchema(), 200, description="")
@tenant_authentication
async def schemas_get(request: web.BaseRequest):
    """Request handler for getting all schemas.

    Args:
        request: aiohttp request object

    Returns:
        The schema identifiers created by the profile.

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


async def register(app: web.Application) -> None:
    """Register routes."""
    app.add_routes(
        [
            web.post("/anoncreds/schema", schemas_post),
            web.get("/anoncreds/schema/{schema_id}", schema_get, allow_head=False),
            web.get("/anoncreds/schemas", schemas_get, allow_head=False),
        ]
    )


def post_process_routes(app: web.Application) -> None:
    """Amend swagger API."""
    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": SCHEMAS_TAG_TITLE,
            "description": "AnonCreds schema management",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
