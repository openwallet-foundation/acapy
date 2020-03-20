"""All route_coordination routes."""

from aiohttp import web
from aiohttp_apispec import docs, response_schema, request_schema

from marshmallow import fields, Schema

from ...connections.models.connection_record import ConnectionRecord
from ...storage.error import StorageNotFoundError
from .manager import RouteCoordinationManager

from .models.route_coordination import RouteCoordinationSchema
from .models.routing_key import RoutingKeySchema
from .models.routing_term import RoutingTermSchema


class MediationRequestSchema(Schema):
    """Request schema for requesting new mediation."""

    recipient_terms = fields.List(fields.Str, required=False)


class MediationRequestResultSchema(RouteCoordinationSchema):
    """Result schema for a mediation request."""

    route_coordination = fields.Nested(RouteCoordinationSchema())
    mediator_terms = fields.List(fields.Nested(RoutingKeySchema()))
    recipient_terms = fields.List(fields.Nested(RoutingTermSchema()))
    routing_keys = fields.List(fields.Nested(RoutingTermSchema()))


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

    try:
        connection = await ConnectionRecord.retrieve_by_id(context, connection_id)
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    route_coordination_manager = RouteCoordinationManager(context)
    (
        route_coordination,
        recipient_terms
    ) = await route_coordination_manager.create_mediation_request(
        connection_id=connection.connection_id, recipient_terms=recipient_terms
    )
    response = {
        'route_coordination': route_coordination.serialize(),
        'recipient_terms': [term.serialize() for term in recipient_terms],
        'mediator_terms': [],
        'routing_keys': []
    }
    return web.json_response(response)


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [web.post(
            "/route-coordination/{connection_id}/create-request",
            create_mediation_request
        )]
    )
