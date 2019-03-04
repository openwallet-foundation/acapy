"""Connection handling admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, response_schema

from marshmallow import fields, Schema

from .models.connection_record import ConnectionRecord, ConnectionRecordSchema


class ConnectionListSchema(Schema):
    """Result schema for connection list."""

    results = fields.List(fields.Nested(ConnectionRecordSchema()))


@docs(tags=["connection"], summary="Query agent-to-agent connections")
@response_schema(ConnectionListSchema(), 200)
async def connections_list(request: web.BaseRequest):
    """
    Request handler for the connection records.

    Args:
        request: aiohttp request object

    Returns:
        The connection list response

    """
    context = request.app["request_context"]
    records = await ConnectionRecord.query(context.storage)
    return web.json_response({"results": [record.serialize() for record in records]})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes([web.get("/connections", connections_list)])
