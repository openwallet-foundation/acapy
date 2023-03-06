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
    INDY_SCHEMA_ID,
    INDY_VERSION,
    NATURAL_NUM,
    UUIDFour,
)

LOGGER = logging.getLogger(__name__)

SPEC_URI = ""

schema_id = fields.Str(
    data_key="id", description="Schema identifier", **INDY_SCHEMA_ID
)
class SchemaIdMatchInfo(OpenAPISchema):
    """"""

    schema_id = schema_id


class CredIdMatchInfo(OpenAPISchema):
    """Path parameters and validators for request taking credential id."""

    credential_id = fields.Str(
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
    description="Issuer did", **GENERIC_DID
)  # TODO: get correct validator


class SchemaSchema(OpenAPISchema):
    """Marshmallow schema for indy schema."""

    attrNames = schemaAttrNames
    name = schemaName
    version = schemaVersion
    issuerId = issuerId


class SchemaPostQueryStringSchema(OpenAPISchema):
    """"""

    schema = fields.Nested(SchemaSchema())
    options = fields.Dict(
        description="Options ",
        required=False,
    )
    
class CredDefSchema(OpenAPISchema):
    """"""
    
    tag = 
    schemaId = schema_id
    issuerId = issuerId
    support_revocation = 
    revocation_registry_size =

class CredDefPostOptionsSchema(OpenAPISchema):
    """"""
    endorser_connection_id =
    support_revocation = 
    revocation_registry_size = 
    
class CredDefPostQueryStringSchema(OpenAPISchema):
    """"""
    
    credential_definition = fields.Nested(CredDefSchema())
    options = fields.Nested(CredDefPostOptionsSchema())

class PublicKeysSchema(OpenAPISchema):
    accumKey = fields.Dict(
        example = '{ "z": "1 0BB...386"}'
    )
class RevRegValueSchema(OpenAPISchema):
    """"""
    publicKeys = PublicKeysSchema()
    maxCredNum =  #666,
    tailsLocation =  #"https://my.revocations.tails/tailsfile.txt",
    tailsHash = #"91zvq2cFmBZmHCcLqFyzv7bfehHH5rMhdAG5wTjqy2PE"
class RevRegPostQueryStringSchema(OpenAPISchema):
    """"""
    
    issuerId = issuerId
    revocDefType = #  "CL_ACCUM",
    credDefId = #: "Gs6cQcvrtWoZKsbBhD3dQJ:3:CL:140384:mctc",
    tag = # "MyCustomCredentialDefinition",
    value= fields.Nested(RevRegValueSchema())
        
class SchemaResponseSchema(OpenAPISchema):
    """"""

    schema = fields.Nested(SchemaSchema())
    options = fields.Dict(
        description="Options ",
        required=False,
    )
    schema_id = schema_id
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
    LOGGER.info(f"request mad with, {input}")

    raise NotImplementedError()


@docs(tags=["anoncreds"], summary="")
@match_info_schema(SchemaIdMatchInfo())
@response_schema(SchemaResponseSchema(), 200, description="")
async def schema_get(request: web.BaseRequest):
    context: AdminRequestContext = request["context"]
    schema_id = request.match_info["schema_id"]

    LOGGER.info(f"called with schema_id: {schema_id}")
    raise NotImplementedError()


@docs(tags=["anoncreds"], summary="")
@querystring_schema(SchemasQueryStringSchema())
async def schemas_get(request: web.BaseRequest):
    context: AdminRequestContext = request["context"]
    schema_name = request.query.get("schemaName")
    schema_version = request.query.get("schemaVersion")
    schema_issuer_did = request.query.get("schemaIssuerDid")
    LOGGER.info(
        f"called with schema_name: {schema_name}, schema_version: {schema_version}, schema_issuer_did: {schema_issuer_did}"
    )
    raise NotImplementedError()


@docs(tags=["anoncreds"], summary="")
@request_schema(CredDefPostQueryStringSchema())
async def cred_def_post(request: web.BaseRequest):
    context: AdminRequestContext = request["context"]
    raise NotImplementedError()


@docs(tags=["anoncreds"], summary="")
async def cred_def_get(request: web.BaseRequest):
    context: AdminRequestContext = request["context"]
    raise NotImplementedError()


@docs(tags=["anoncreds"], summary="")
async def cred_defs_get(request: web.BaseRequest):
    context: AdminRequestContext = request["context"]
    raise NotImplementedError()


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/anoncreds/schema", schemas_post, allow_head=False),
            web.get("/anoncreds/schema/{schema_id}", schema_get, allow_head=False),
            web.get("/anoncreds/schemas", schemas_get, allow_head=False),
            web.post(
                "/anoncreds/credential-definition", cred_def_post, allow_head=False
            ),
            web.get(
                "/anoncreds/credential-definition/{credential_definition_id}",
                cred_def_get,
                allow_head=False,
            ),
            web.get(
                "/anoncreds/credential-definitions/issuer/",
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
