""" Anoncreds admin routes """
# import json
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

SPEC_URI = ""

schemaId = fields.Str(
    data_key="schemaId", description="Schema identifier", **INDY_SCHEMA_ID
)


class SchemaIdMatchInfo(OpenAPISchema):
    schema_id = schemaId


class CredIdMatchInfo(OpenAPISchema):
    """Path parameters and validators for request taking credential id."""

    cred_def_id = fields.Str(
        description="Credential identifier", required=True, example=UUIDFour.EXAMPLE
    )


schemaAttrNames = fields.List(
    fields.Str(
        description="Attribute name",
        example="score",
    ),
    description="Schema attribute names",
    data_key="attrNames",
)
schemaName = fields.Str(
    description="Schema name",
    example=INDY_SCHEMA_ID["example"].split(":")[2],
)
schemaVersion = fields.Str(description="Schema version", **INDY_VERSION)
issuerId = fields.Str(
    description="Issuer Identifier of the credential definition or schema",
    **GENERIC_DID,
)  # TODO: get correct validator


class SchemaSchema(OpenAPISchema):
    """Marshmallow schema for indy schema."""

    attrNames = schemaAttrNames
    name = schemaName
    version = schemaVersion
    issuerId = issuerId


class SchemaPostOptionSchema(OpenAPISchema):
    endorser_connection_id = fields.UUID(
        description="Connection identifier (optional)",
        required=False,
        example=UUIDFour.EXAMPLE,
    )


class SchemaPostQueryStringSchema(OpenAPISchema):
    schema = fields.Nested(SchemaSchema())
    options = fields.Nested(SchemaPostOptionSchema())


support_revocation = fields.Bool()
revocation_registry_size = fields.Int()


class CredDefSchema(OpenAPISchema):
    tag = fields.Str(
        description="The tag value passed in by the Issuer to an AnonCred's Credential Definition create and store implementation."
    )
    schemaId = schemaId
    issuerId = issuerId
    supportRevocation = support_revocation
    revocationRegistrySize = revocation_registry_size


class CredDefPostOptionsSchema(OpenAPISchema):
    endorserConnectionId = fields.Str()
    supportRevocation = support_revocation
    revocationRegistrySize = revocation_registry_size


class CredDefPostQueryStringSchema(OpenAPISchema):
    credentialDefinition = fields.Nested(CredDefSchema())
    options = fields.Nested(CredDefPostOptionsSchema())


class CredDefsQueryStringSchema(OpenAPISchema):
    credentialDefinitionId = fields.Str(
        description="Credential definition identifier",
        **INDY_CRED_DEF_ID,
    )
    issuerId = issuerId
    schemaId = schemaId
    schemaIssuerId = issuerId
    schemaName = schemaName
    schemaVersion = schemaVersion


# class CredDefResponseSchema(OpenAPISchema):


'''
class PublicKeysSchema(OpenAPISchema):
    accumKey = fields.Dict(example='{ "z": "1 0BB...386"}')


class RevRegValueSchema(OpenAPISchema):
    """"""

    publicKeys = PublicKeysSchema()
    maxCredNum = fields.Int(
        description=" The capacity of the Revocation Registry, a count of the number of credentials that can be issued using the Revocation Registry.",
        example=777,
    )
    tailsLocation = fields.URL(
        description="The capacity of the Revocation Registry, a count of the number of credentials that can be issued using the Revocation Registry."
    )
    tailsHash = fields.Str()  # "91zvq2cFmBZmHCcLqFyzv7bfehHH5rMhdAG5wTjqy2PE"


class RevRegPostQueryStringSchema(OpenAPISchema):
    """"""

    issuerId = issuerId
    revocDefType = fields.Str()  # always  "CL_ACCUM",
    credDefId = INDY_CRED_DEF_ID  #: "Gs6cQcvrtWoZKsbBhD3dQJ:3:CL:140384:mctc",
    tag = fields.Str()
    value = fields.Nested(RevRegValueSchema())
'''


class SchemaResponseSchema(OpenAPISchema):
    """"""

    schema = fields.Nested(SchemaSchema())
    options = fields.Dict(
        description="Options ",
        required=False,
    )
    schema_id = schemaId
    resolution_metadata = fields.Dict()
    schema_metadata = fields.Dict()


class SchemasQueryStringSchema(OpenAPISchema):
    """"""

    schemaName = schemaName
    schemaVersion = schemaVersion
    schemaIssuerDid = issuerId


@docs(tags=["anoncreds"], summary="")
@request_schema(SchemaPostQueryStringSchema())
async def schemas_post(request: web.BaseRequest):
    context: AdminRequestContext = request["context"]
    input = await request.json()

    return web.json_response({"input": input})


@docs(tags=["anoncreds"], summary="")
@match_info_schema(SchemaIdMatchInfo())
@response_schema(SchemaResponseSchema(), 200, description="")
async def schema_get(request: web.BaseRequest):
    context: AdminRequestContext = request["context"]
    schema_id = request.match_info["schemaId"]

    return web.json_response({"schema_id": schema_id})


@docs(tags=["anoncreds"], summary="")
@querystring_schema(SchemasQueryStringSchema())
async def schemas_get(request: web.BaseRequest):
    context: AdminRequestContext = request["context"]
    schema_issuer_did = request.query.get("schemaIssuerDid")
    schema_name = request.query.get("schemaName")
    schema_version = request.query.get("schemaVersion")

    return web.json_response(
        {
            "schema_issuer_did": schema_issuer_did,
            "schema_name": schema_name,
            "schema_version": schema_version,
        }
    )


@docs(tags=["anoncreds"], summary="")
@request_schema(CredDefPostQueryStringSchema())
async def cred_def_post(request: web.BaseRequest):
    context: AdminRequestContext = request["context"]
    input = await request.json()
    return web.json_response({"input": input})


@docs(tags=["anoncreds"], summary="")
@match_info_schema(CredIdMatchInfo())
async def cred_def_get(request: web.BaseRequest):
    context: AdminRequestContext = request["context"]
    credential_id = request.match_info["cred_def_id"]
    return web.json_response({"cred_def_id": credential_id})


@docs(tags=["anoncreds"], summary="")
@querystring_schema(CredDefsQueryStringSchema())
async def cred_defs_get(request: web.BaseRequest):
    context: AdminRequestContext = request["context"]
    cred_def_id = request.query.get("credentialDefinitionId")
    issuer_id = request.query.get("issuerId")
    schema_id = request.query.get("schemaId")
    schema_issuer_id = request.query.get("schemaIssuerId")
    schema_name = request.query.get("schemaName")
    schema_version = request.query.get("schemaVersion")

    return web.json_response(
        {
            "cred_def_id": cred_def_id,
            "issuer_id": issuer_id,
            "schema_id": schema_id,
            "schema_issuer_id": schema_issuer_id,
            "schema_name": schema_name,
            "schema_version": schema_version,
        }
    )


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
