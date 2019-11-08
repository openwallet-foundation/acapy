"""Credential schema admin routes."""

from asyncio import shield

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema

from marshmallow import fields, Schema

from ...ledger.base import BaseLedger
from ...storage.base import BaseStorage
from ..valid import INDY_SCHEMA_ID, INDY_VERSION
from .util import SCHEMA_SENT_RECORD_TYPE, SCHEMA_TAGS


class SchemaSendRequestSchema(Schema):
    """Request schema for schema send request."""

    schema_name = fields.Str(
        required=True,
        description="Schema name",
        example="prefs",
    )
    schema_version = fields.Str(
        required=True,
        description="Schema version",
        **INDY_VERSION
    )
    attributes = fields.List(
        fields.Str(
            description="attribute name",
            example="score",
        ),
        required=True,
        description="List of schema attributes"
    )


class SchemaSendResultsSchema(Schema):
    """Results schema for schema send request."""

    schema_id = fields.Str(
        description="Schema identifier",
        **INDY_SCHEMA_ID
    )


class SchemaSchema(Schema):
    """Content for returned schema."""

    ver = fields.Str(
        description="Node protocol version",
        **INDY_VERSION
    )
    ident = fields.Str(
        data_key="id",
        description="Schema identifier",
        **INDY_SCHEMA_ID
    )
    name = fields.Str(
        description="Schema name",
        example=INDY_SCHEMA_ID["example"].split(":")[2],
    )
    version = fields.Str(
        description="Schema version",
        **INDY_VERSION
    )
    attr_names = fields.List(
        fields.Str(
            description="Attribute name",
            example="score",
        ),
        description="Schema attribute names",
    )
    seqNo = fields.Integer(
        description="Schema sequence number",
        example=999
    )


class SchemaGetResultsSchema(Schema):
    """Results schema for schema get request."""

    schema_json = fields.Nested(SchemaSchema())


class SchemasCreatedResultsSchema(Schema):
    """Results schema for a schemas-created request."""

    schema_ids = fields.List(
        fields.Str(
            description="Schema identifiers",
            **INDY_SCHEMA_ID
        )
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

    ledger: BaseLedger = await context.inject(BaseLedger)
    async with ledger:
        schema_id = await shield(
            ledger.send_schema(schema_name, schema_version, attributes)
        )

    return web.json_response({"schema_id": schema_id})


@docs(
    tags=["schema"],
    parameters=[
        {
            "name": p,
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        } for p in SCHEMA_TAGS
    ],
    summary="Search for matching schema that agent originated",
)
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

    storage = await context.inject(BaseStorage)
    found = await storage.search_records(
        type_filter=SCHEMA_SENT_RECORD_TYPE,
        tag_query={
            p: request.query[p] for p in SCHEMA_TAGS if p in request.query
        }
    ).fetch_all()

    return web.json_response({"schema_ids": [record.value for record in found]})


@docs(tags=["schema"], summary="Gets a schema from the ledger")
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

    schema_id = request.match_info["id"]

    ledger: BaseLedger = await context.inject(BaseLedger)
    async with ledger:
        schema = await ledger.get_schema(schema_id)

    return web.json_response({"schema_json": schema})


async def register(app: web.Application):
    """Register routes."""
    app.add_routes([web.post("/schemas", schemas_send_schema)])
    app.add_routes([web.get("/schemas/created", schemas_created)])
    app.add_routes([web.get("/schemas/{id}", schemas_get_schema)])
