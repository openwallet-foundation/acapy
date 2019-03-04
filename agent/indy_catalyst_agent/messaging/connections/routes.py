"""Connection handling admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, response_schema

from marshmallow import fields, Schema

from .models.connection_record import ConnectionRecord, ConnectionRecordSchema
from ...storage.error import StorageNotFoundError


class ConnectionListSchema(Schema):
    """Result schema for connection list."""

    results = fields.List(fields.Nested(ConnectionRecordSchema()))


@docs(
    tags=["connection"],
    summary="Query agent-to-agent connections",
    parameters=[
        {
            "name": "initiator",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
        {
            "name": "invitation_key",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
        {
            "name": "my_did",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
        {
            "name": "state",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
        {
            "name": "their_did",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
        {
            "name": "their_role",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
    ],
)
@response_schema(ConnectionListSchema(), 200)
async def connections_list(request: web.BaseRequest):
    """
    Request handler for searching connection records.

    Args:
        request: aiohttp request object

    Returns:
        The connection list response

    """
    context = request.app["request_context"]
    tag_filter = {}
    for param_name in (
        "initiator",
        "invitation_id",
        "my_did",
        "state",
        "their_did",
        "their_role",
    ):
        if param_name in request.query and request.query[param_name] != "":
            tag_filter[param_name] = request.query[param_name]
    records = await ConnectionRecord.query(context.storage, tag_filter)
    return web.json_response({"results": [record.serialize() for record in records]})


@docs(tags=["connection"], summary="Fetch a single connection record")
@response_schema(ConnectionRecordSchema(), 200)
async def connections_retrieve(request: web.BaseRequest):
    """
    Request handler for fetching a single connection record.

    Args:
        request: aiohttp request object

    Returns:
        The connection record response

    """
    context = request.app["request_context"]
    connection_id = request.match_info["id"]
    try:
        record = await ConnectionRecord.retrieve_by_id(context.storage, connection_id)
    except StorageNotFoundError:
        return web.HTTPNotFound()
    return web.json_response(record.serialize())


async def register(app: web.Application):
    """Register routes."""

    app.add_routes([web.get("/connections", connections_list)])
    app.add_routes([web.get("/connections/{id}", connections_retrieve)])
