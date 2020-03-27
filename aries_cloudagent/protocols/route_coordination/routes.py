"""All route_coordination routes."""

from aiohttp import web
from aiohttp_apispec import docs, response_schema, request_schema

from marshmallow import fields, Schema

from ...connections.models.connection_record import ConnectionRecord
from ...storage.error import StorageNotFoundError
from .manager import RouteCoordinationManager

from .models.route_coordination import RouteCoordination, RouteCoordinationSchema
from .messages.inner.keylist_update_rule import KeylistUpdateRuleSchema


class MediationRequestSchema(Schema):
    """Request schema for requesting new mediation."""

    recipient_terms = fields.List(fields.Str, required=False)
    mediator_terms = fields.List(fields.Str, required=False)


class MediationRequestResultSchema(Schema):
    """Result schema for a mediation request."""

    route_coordination = fields.Nested(RouteCoordinationSchema())


class RoutingListResultSchema(Schema):
    """Result schema for routing list."""

    results = fields.List(
        fields.Nested(RouteCoordinationSchema()),
        description="List of mediation records",
    )


class MediationDenySchema(Schema):
    """Request schema for requesting new mediation."""

    recipient_terms = fields.List(fields.Str, required=False)
    mediator_terms = fields.List(fields.Str, required=False)


class KeylistUpdateRequest(Schema):
    """Request schema for updating keys."""

    updates = fields.List(
        fields.Nested(KeylistUpdateRuleSchema()),
        description="List of key updates",
    )


class KeylistUpdateResponse(Schema):
    """Response schema for updating keys."""

    updates = fields.List(
        fields.Nested(KeylistUpdateRuleSchema()),
        description="List of key updates",
    )


class KeylistQueryRequest(Schema):
    """Request schema for keylist query."""

    limit = fields.Int(
        description="Total message count for query",
    )
    offset = fields.Int(
        description="Offset value for query",
    )
    filter = fields.Dict(
        description="Query dictionary object",
        example={
            "routing_key": [
                "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV",
                "2wUJCoyzkJz1tTxehfT7Usq5FgJz3EQHBQC7b2mXxbRZ"
            ]
        }
    )


class KeylistQueryResponse(Schema):
    """Response schema for keylist query."""

    route_coordination_id = fields.Str(
        description="Route coordination identifier to query",
        required=False
    )


@docs(tags=["route-coordination"], summary="Creates a new mediation request")
@request_schema(MediationRequestSchema())
@response_schema(MediationRequestResultSchema(), 200)
async def create_mediation_request(request: web.BaseRequest):
    """
    Request handler for creating a new mediation request.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    # outbound_handler = request.app["outbound_message_router"]

    body = await request.json()

    connection_id = request.match_info["connection_id"]
    recipient_terms = body.get("recipient_terms")
    mediator_terms = body.get("mediator_terms")

    try:
        connection = await ConnectionRecord.retrieve_by_id(context, connection_id)
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    route_coordination_manager = RouteCoordinationManager(context)
    route_coordination = await route_coordination_manager.create_mediation_request(
        connection_id=connection.connection_id,
        recipient_terms=recipient_terms,
        mediator_terms=mediator_terms
    )
    return web.json_response(route_coordination.serialize())


def route_coordination_sort(coord):
    """Get the sorting key for a particular route coordination."""
    return coord["created_at"]


@docs(
    tags=["route-coordination"],
    summary="Query route coordination records",
    parameters=[
        {
            "name": "connection_id",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
        {
            "name": "route_coordination_id",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
        {
            "name": "initiator",
            "in": "query",
            "schema": {"type": "string", "enum": ["self", "external"]},
            "required": False,
        },
        {
            "name": "state",
            "in": "query",
            "schema": {
                "type": "string",
                "enum": [
                    "mediation_request",
                    "mediation_sent",
                    "mediation_received",
                    "mediation_granted",
                    "mediation_denied",
                    "mediation_canceled",
                ],
            },
            "required": False,
        },
        {
            "name": "role",
            "in": "query",
            "schema": {"type": "string", "enum": ["mediator", "recipient"]},
            "required": False,
        },
    ],
)
@response_schema(RoutingListResultSchema(), 200)
async def routing_list(request: web.BaseRequest):
    """
    Request handler for searching route coordinations.

    Args:
        request: aiohttp request object

    Returns:
        The connection list response

    """
    context = request.app["request_context"]
    tag_filter = {}
    for param_name in (
        "connection_id",
        "route_coordination_id",
    ):
        if param_name in request.query and request.query[param_name] != "":
            tag_filter[param_name] = request.query[param_name]
    post_filter = {}
    for param_name in (
        "initiator",
        "state",
        "role",
    ):
        if param_name in request.query and request.query[param_name] != "":
            post_filter[param_name] = request.query[param_name]
    records = await RouteCoordination.query(context, tag_filter, post_filter)
    results = [record.serialize() for record in records]
    results.sort(key=route_coordination_sort)

    return web.json_response({"results": results})


@docs(tags=["route-coordination"], summary="Accept a stored route coordination request")
@response_schema(RouteCoordinationSchema(), 200)
async def grant_mediate_request(request: web.BaseRequest):
    """
    Request handler for accepting a stored route coordination request.

    Args:
        request: aiohttp request object

    Returns:
        The resulting route coordination record details

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    route_coordination_id = request.match_info["id"]

    try:
        route_coordination = await RouteCoordination.retrieve_by_id(
            context,
            route_coordination_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, route_coordination.connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()
    route_coordination_manager = RouteCoordinationManager(context)

    response, routing_record = await route_coordination_manager.create_accept_response(
        route_coordination
    )
    await outbound_handler(response, connection_id=connection_record.connection_id)
    return web.json_response(routing_record.serialize())


@docs(tags=["route-coordination"], summary="Deny a stored route coordination request")
@request_schema(MediationDenySchema())
@response_schema(RouteCoordinationSchema(), 200)
async def deny_mediate_request(request: web.BaseRequest):
    """
    Request handler for denying a stored route coordination request.

    Args:
        request: aiohttp request object

    Returns:
        The resulting route coordination record details

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()

    route_coordination_id = request.match_info["id"]
    recipient_terms = body.get("recipient_terms")
    mediator_terms = body.get("mediator_terms")

    try:
        route_coordination = await RouteCoordination.retrieve_by_id(
            context,
            route_coordination_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, route_coordination.connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()
    route_coordination_manager = RouteCoordinationManager(context)

    response, routing_record = await route_coordination_manager.create_deny_response(
        route_coordination=route_coordination,
        mediator_terms=mediator_terms,
        recipient_terms=recipient_terms
    )
    await outbound_handler(response, connection_id=connection_record.connection_id)
    return web.json_response(routing_record.serialize())


@docs(tags=["route-coordination"], summary="Create a keylist update request")
@request_schema(KeylistUpdateRequest())
@response_schema(KeylistUpdateResponse(), 200)
async def keylist_update(request: web.BaseRequest):
    """
    Request handler for updating keylist.

    Args:
        request: aiohttp request object

    Returns:
        The resulting route coordination record details

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()

    route_coordination_id = request.match_info["id"]
    updates = body.get("updates")

    try:
        route_coordination = await RouteCoordination.retrieve_by_id(
            context,
            route_coordination_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, route_coordination.connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()

    route_coordination_manager = RouteCoordinationManager(context)

    request = await route_coordination_manager.create_keylist_update_request(
        updates=updates,
    )

    await outbound_handler(request, connection_id=connection_record.connection_id)
    return web.json_response({"updates": updates})


@docs(tags=["route-coordination"], summary="Create a keylist query request")
@request_schema(KeylistQueryRequest())
@response_schema(KeylistQueryResponse(), 200)
async def keylist_query(request: web.BaseRequest):
    """
    Request handler for denying a stored route coordination request.

    Args:
        request: aiohttp request object

    Returns:
        The resulting route coordination record details

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()

    route_coordination_id = request.match_info["id"]
    limit = body.get("limit")
    offset = body.get("offset")
    filter = body.get("filter")

    try:
        route_coordination = await RouteCoordination.retrieve_by_id(
            context,
            route_coordination_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, route_coordination.connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()

    route_coordination_manager = RouteCoordinationManager(context)

    request = await route_coordination_manager.create_keylist_query_request_request(
        limit=limit,
        offset=offset,
        filter=filter
    )

    await outbound_handler(request, connection_id=connection_record.connection_id)
    return web.json_response(
        {
            "route_coordination_id": route_coordination.connection_id
        }
    )


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post(
                "/route-coordination/{connection_id}/create-request",
                create_mediation_request
            ),
            web.post(
                "/route-coordination/list",
                routing_list
            ),
            web.post(
                "/route-coordination/{id}/grant-request",
                grant_mediate_request
            ),
            web.post(
                "/route-coordination/{id}/deny-request",
                deny_mediate_request
            ),
            web.post(
                "/route-coordination/{id}/keylist_update",
                keylist_update
            ),
            web.post(
                "/route-coordination/{id}/keylist_query",
                keylist_query
            ),
        ]
    )
