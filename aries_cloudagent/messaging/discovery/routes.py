"""Protocol discovery admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, response_schema

from marshmallow import fields, Schema

from ..protocol_registry import ProtocolRegistry


class QueryResultSchema(Schema):
    """Result schema for connection list."""

    results = fields.Dict(fields.Str(), fields.Dict())


@docs(
    tags=["server"],
    summary="Query supported protocols",
    parameters=[
        {
            "name": "query",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        }
    ],
)
@response_schema(QueryResultSchema(), 200)
async def query_protocols(request: web.BaseRequest):
    """
    Request handler for inspecting supported protocols.

    Args:
        request: aiohttp request object

    Returns:
        The diclosed protocols response

    """
    context = request.app["request_context"]
    registry: ProtocolRegistry = await context.inject(ProtocolRegistry)
    results = registry.protocols_matching_query(request.query.get("query", "*"))

    return web.json_response({"results": {k: {} for k in results}})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes([web.get("/protocols", query_protocols)])
