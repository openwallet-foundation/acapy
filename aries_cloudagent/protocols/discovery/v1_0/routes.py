"""Feature discovery admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, response_schema
from marshmallow import fields

from ....admin.request_context import AdminRequestContext
from ....core.protocol_registry import ProtocolRegistry
from ....messaging.models.openapi import OpenAPISchema

from .message_types import SPEC_URI


class QueryResultSchema(OpenAPISchema):
    """Result schema for the protocol list."""

    results = fields.Dict(
        keys=fields.Str(description="protocol"),
        values=fields.Dict(description="Protocol descriptor"),
        description="Query results keyed by protocol",
    )


class QueryFeaturesQueryStringSchema(OpenAPISchema):
    """Query string parameters for feature query."""

    query = fields.Str(description="Query", required=False, example="did:sov:*")


@docs(
    tags=["server"],
    summary="Query supported features",
)
@querystring_schema(QueryFeaturesQueryStringSchema())
@response_schema(QueryResultSchema(), 200)
async def query_features(request: web.BaseRequest):
    """
    Request handler for inspecting supported protocols.

    Args:
        request: aiohttp request object

    Returns:
        The diclosed protocols response

    """
    context: AdminRequestContext = request["context"]
    registry: ProtocolRegistry = context.inject(ProtocolRegistry)
    results = registry.protocols_matching_query(request.query.get("query", "*"))

    return web.json_response({"results": {k: {} for k in results}})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes([web.get("/features", query_features, allow_head=False)])


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "server",
            "description": "Feature discovery",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
