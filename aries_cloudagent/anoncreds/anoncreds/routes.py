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


credentialDefinitionId = fields.Str(
    description="Credential definition identifier",
    **INDY_CRED_DEF_ID,
)


class CredDefsQueryStringSchema(OpenAPISchema):
    credentialDefinitionId = credentialDefinitionId
    issuerId = issuerId
    schemaId = schemaId
    schemaIssuerId = issuerId
    schemaName = schemaName
    schemaVersion = schemaVersion


"""
"primary": {
    "n": "779...397",
    "r": {
    "link_secret": "521...922",
    "<key>": "410...200"
    },
    "rctxt": "774...977",
    "s": "750..893",
    "z": "632...005"
}
"""


class PrimarySchema(OpenAPISchema):
    n = fields.Str(example="779...397")
    r = fields.Dict()
    rctxt = fields.Str(example="774...977")
    s = fields.Str(example="750..893")
    z = fields.Str(example="632...005")


class CredDefValueSchema(OpenAPISchema):
    primary = fields.Nested(PrimarySchema())


class CredDefResponseSchema(OpenAPISchema):
    issuerId = issuerId
    schemaId = schemaId
    tag = fields.Str(
        description="The tag value passed in by the Issuer to an AnonCred's Credential Definition create and store implementation."
    )
    value = fields.Nested(CredDefValueSchema())
    # registration_metadata = support_revocation
    # revocationRegistrySize = revocation_registry_size


class CredDefState(OpenAPISchema):
    state = fields.Str()  # TODO: create validator for only possible states
    credential_definition_id = credentialDefinitionId
    credential_definition = fields.Nested(CredDefResponseSchema())


class PostCredDefResponseSchema(OpenAPISchema):
    job_id = fields.Str()
    credential_definition_state = fields.Nested(CredDefState())
    registration_metadata = fields.Dict()
    credential_definition_metadata = fields.Dict()


class GetCredDefResponseSchema(OpenAPISchema):
    credential_definition_id = credentialDefinitionId
    credential_definition = fields.Nested(CredDefResponseSchema())
    resolution_metadata = fields.Dict()
    credential_definition_metadata = fields.Dict()


class GetCredDefsResponseSchema(OpenAPISchema):
    credential_definition_id = fields.Str()


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


class SchemaState(OpenAPISchema):
    state = fields.Str()  # TODO: create validator for only possible states
    schema_id = schemaId
    schema = fields.Nested(SchemaSchema())


class PostSchemaResponseSchema(OpenAPISchema):
    job_id = fields.Str()
    schema_state = fields.Nested(SchemaState())
    registration_metadata = (
        fields.Dict()
    )  # For indy, schema_metadata will contain the seqNo
    schema_metadata = fields.Dict()


class SchemaResponseSchema(OpenAPISchema):
    schema = fields.Nested(SchemaSchema())
    options = fields.Dict(
        description="Options ",
        required=False,
    )
    schema_id = schemaId
    resolution_metadata = fields.Dict()
    schema_metadata = fields.Dict()


class SchemasResponseSchema(OpenAPISchema):
    schema_id = fields.List(schemaId)


class SchemasQueryStringSchema(OpenAPISchema):
    schemaName = schemaName
    schemaVersion = schemaVersion
    schemaIssuerDid = issuerId


@docs(tags=["anoncreds"], summary="")
@request_schema(SchemaPostQueryStringSchema())
@response_schema(PostSchemaResponseSchema(), 200, description="")
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
@response_schema(SchemasResponseSchema(), 200, description="")
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
@response_schema(PostCredDefResponseSchema(), 200, description="")
async def cred_def_post(request: web.BaseRequest):
    context: AdminRequestContext = request["context"]
    input = await request.json()
    return web.json_response({"input": input})


@docs(tags=["anoncreds"], summary="")
@match_info_schema(CredIdMatchInfo())
@response_schema(GetCredDefResponseSchema(), 200, description="")
async def cred_def_get(request: web.BaseRequest):
    context: AdminRequestContext = request["context"]
    credential_id = request.match_info["cred_def_id"]
    return web.json_response({"cred_def_id": credential_id})


@docs(tags=["anoncreds"], summary="")
@querystring_schema(CredDefsQueryStringSchema())
@response_schema(GetCredDefsResponseSchema(), 200, description="")
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
