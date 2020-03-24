"""All route_coordination routes."""

from aiohttp import web
from aiohttp_apispec import docs, response_schema, request_schema

from marshmallow import fields, Schema

from ...connections.models.connection_record import ConnectionRecord
from ...storage.error import StorageNotFoundError
from .manager import RouteCoordinationManager

from .models.route_coordination import RouteCoordination, RouteCoordinationSchema


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
        ]
    )
