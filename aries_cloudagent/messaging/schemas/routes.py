"""Credential schema admin routes."""

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
from marshmallow.validate import Regexp

from ...indy.issuer import IndyIssuer, IndyIssuerError
from ...ledger.base import BaseLedger
from ...ledger.error import LedgerError
from ...storage.base import BaseStorage
from ..models.openapi import OpenAPISchema
from ..valid import B58, NATURAL_NUM, INDY_SCHEMA_ID, INDY_VERSION
from .util import SchemaQueryStringSchema, SCHEMA_SENT_RECORD_TYPE, SCHEMA_TAGS


class SchemaSendRequestSchema(OpenAPISchema):
    """Request schema for schema send request."""

    schema_name = fields.Str(
        required=True,
        description="Schema name",
        example="prefs",
    )
    schema_version = fields.Str(
        required=True, description="Schema version", **INDY_VERSION
    )
    attributes = fields.List(
        fields.Str(
            description="attribute name",
            example="score",
        ),
        required=True,
        description="List of schema attributes",
    )


class SchemaSendResultsSchema(OpenAPISchema):
    """Results schema for schema send request."""

    schema_id = fields.Str(
        description="Schema identifier", required=True, **INDY_SCHEMA_ID
    )
    schema = fields.Dict(description="Schema result", required=True)


class SchemaSchema(OpenAPISchema):
    """Content for returned schema."""

    ver = fields.Str(description="Node protocol version", **INDY_VERSION)
    ident = fields.Str(data_key="id", description="Schema identifier", **INDY_SCHEMA_ID)
    name = fields.Str(
        description="Schema name",
        example=INDY_SCHEMA_ID["example"].split(":")[2],
    )
    version = fields.Str(description="Schema version", **INDY_VERSION)
    attr_names = fields.List(
        fields.Str(
            description="Attribute name",
            example="score",
        ),
        description="Schema attribute names",
        data_key="attrNames",
    )
    seqNo = fields.Int(description="Schema sequence number", strict=True, **NATURAL_NUM)


class SchemaGetResultsSchema(OpenAPISchema):
    """Results schema for schema get request."""

    schema = fields.Nested(SchemaSchema())


class SchemasCreatedResultsSchema(OpenAPISchema):
    """Results schema for a schemas-created request."""

    schema_ids = fields.List(
        fields.Str(description="Schema identifiers", **INDY_SCHEMA_ID)
    )


class SchemaIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking schema id."""

    schema_id = fields.Str(
        description="Schema identifier",
        required=True,
        validate=Regexp(rf"^[1-9][0-9]*|[{B58}]{{21,22}}:2:.+:[0-9.]+$"),
        example=INDY_SCHEMA_ID["example"],
    )


@docs(tags=["schema"], summary="Sends a schema to the ledger")
@request_schema(SchemaSendRequestSchema())
@response_schema(SchemaSendResultsSchema(), 200)
async def schemas_send_schema(request: web.BaseRequest):
    """
    Request handler for sending a credential offer.

    Args:
        request: aiohttp request object

    Returns:
        The schema id sent

    """
    context = request.app["request_context"]

    body = await request.json()

    schema_name = body.get("schema_name")
    schema_version = body.get("schema_version")
    attributes = body.get("attributes")

    session = await context.session()
    ledger = session.inject(BaseLedger, required=False)
    if not ledger:
        reason = "No ledger available"
        if not session.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)

    issuer = session.inject(IndyIssuer)
    async with ledger:
        try:
            schema_id, schema_def = await shield(
                ledger.create_and_send_schema(
                    issuer, schema_name, schema_version, attributes
                )
            )
        except (IndyIssuerError, LedgerError) as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"schema_id": schema_id, "schema": schema_def})


@docs(
    tags=["schema"],
    summary="Search for matching schema that agent originated",
)
@querystring_schema(SchemaQueryStringSchema())
@response_schema(SchemasCreatedResultsSchema(), 200)
async def schemas_created(request: web.BaseRequest):
    """
    Request handler for retrieving schemas that current agent created.

    Args:
        request: aiohttp request object

    Returns:
        The identifiers of matching schemas

    """
    context = request.app["request_context"]

    session = await context.session()
    storage = session.inject(BaseStorage)
    found = await storage.search_records(
        type_filter=SCHEMA_SENT_RECORD_TYPE,
        tag_query={
            tag: request.query[tag] for tag in SCHEMA_TAGS if tag in request.query
        },
    ).fetch_all()

    return web.json_response({"schema_ids": [record.value for record in found]})


@docs(tags=["schema"], summary="Gets a schema from the ledger")
@match_info_schema(SchemaIdMatchInfoSchema())
@response_schema(SchemaGetResultsSchema(), 200)
async def schemas_get_schema(request: web.BaseRequest):
    """
    Request handler for sending a credential offer.

    Args:
        request: aiohttp request object

    Returns:
        The schema details.

    """
    context = request.app["request_context"]

    schema_id = request.match_info["schema_id"]

    session = await context.session()
    ledger = session.inject(BaseLedger, required=False)
    if not ledger:
        reason = "No ledger available"
        if not session.settings.get_value("wallet.type"):
            reason += ": missing wallet-type?"
        raise web.HTTPForbidden(reason=reason)

    async with ledger:
        try:
            schema = await ledger.get_schema(schema_id)
        except LedgerError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"schema": schema})


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            web.post("/schemas", schemas_send_schema),
            web.get("/schemas/created", schemas_created, allow_head=False),
            web.get("/schemas/{schema_id}", schemas_get_schema, allow_head=False),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "schema",
            "description": "Schema operations",
            "externalDocs": {
                "description": "Specification",
                "url": (
                    "https://github.com/hyperledger/indy-node/blob/master/"
                    "design/anoncreds.md#schema"
                ),
            },
        }
    )
