"""AnonCreds credential definition routes."""

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)
from marshmallow import fields

from ....admin.decorators.auth import tenant_authentication
from ....admin.request_context import AdminRequestContext
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import (
    ANONCREDS_CRED_DEF_ID_EXAMPLE,
    ANONCREDS_DID_EXAMPLE,
    ANONCREDS_SCHEMA_ID_EXAMPLE,
)
from ....utils.profiles import is_not_anoncreds_profile_raise_web_exception
from ...base import AnonCredsObjectNotFound, AnonCredsResolutionError
from ...issuer import AnonCredsIssuer, AnonCredsIssuerError
from ...models.credential_definition import CredDefResultSchema, GetCredDefResultSchema
from ...registry import AnonCredsRegistry
from ...util import handle_value_error
from ..common import (
    create_transaction_for_endorser_description,
    endorser_connection_id_description,
)

CRED_DEF_TAG_TITLE = "AnonCreds - Credential Definitions"


class CredIdMatchInfo(OpenAPISchema):
    """Path parameters and validators for request taking credential id."""

    cred_def_id = fields.Str(
        metadata={
            "description": "Credential definition identifier",
            "example": ANONCREDS_CRED_DEF_ID_EXAMPLE,
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
            "example": ANONCREDS_SCHEMA_ID_EXAMPLE,
        },
        required=True,
        data_key="schemaId",
    )
    issuer_id = fields.Str(
        metadata={
            "description": "Issuer Identifier of the credential definition",
            "example": ANONCREDS_DID_EXAMPLE,
        },
        required=True,
        data_key="issuerId",
    )


class CredDefPostOptionsSchema(OpenAPISchema):
    """Parameters and validators for credential definition options."""

    endorser_connection_id = fields.Str(
        metadata={
            "description": endorser_connection_id_description,
            "example": "UUIDFour.EXAMPLE",
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
            "example": ANONCREDS_DID_EXAMPLE,
        }
    )
    schema_id = fields.Str(
        metadata={
            "description": "Schema identifier",
            "example": ANONCREDS_SCHEMA_ID_EXAMPLE,
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
    tags=[CRED_DEF_TAG_TITLE],
    summary="Create a credential definition on the connected datastore",
)
@request_schema(CredDefPostRequestSchema())
@response_schema(CredDefResultSchema(), 200, description="")
@tenant_authentication
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
    tags=[CRED_DEF_TAG_TITLE],
    summary="Retrieve an individual credential definition details",
)
@match_info_schema(CredIdMatchInfo())
@response_schema(GetCredDefResultSchema(), 200, description="")
@tenant_authentication
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
    tags=[CRED_DEF_TAG_TITLE],
    summary="Retrieve all credential definition ids",
)
@querystring_schema(CredDefsQueryStringSchema())
@response_schema(GetCredDefsResponseSchema(), 200, description="")
@tenant_authentication
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


async def register(app: web.Application) -> None:
    """Register routes."""

    app.add_routes(
        [
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
        ]
    )


def post_process_routes(app: web.Application) -> None:
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": CRED_DEF_TAG_TITLE,
            "description": "AnonCreds credential definition management",
            "externalDocs": {
                "description": "Specification",
                "url": "https://hyperledger.github.io/anoncreds-spec",
            },
        }
    )
