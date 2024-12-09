"""Trust ping admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, match_info_schema, request_schema, response_schema
from marshmallow import fields
from didcomm_messaging import DIDCommMessaging, RoutingService
from didcomm_messaging.resolver import DIDResolver as DMPResolver

from ....admin.decorators.auth import tenant_authentication
from ....admin.request_context import AdminRequestContext
from ....connections.models.conn_record import ConnRecord
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import UUID4_EXAMPLE
from ....storage.error import StorageNotFoundError
from .message_types import SPEC_URI
from .messages.ping import Ping


class PingRequestSchema(OpenAPISchema):
    """Request schema for performing a ping."""

    to = fields.Str(
        required=True,
        allow_none=False,
        metadata={"description": "Comment for the ping message"},
    )
    response_requested = fields.Bool(
        required=False,
        allow_none=True,
        metadata={"description": "Comment for the ping message"},
    )


class PingRequestResponseSchema(OpenAPISchema):
    """Request schema for performing a ping."""

    thread_id = fields.Str(
        required=False, metadata={"description": "Thread ID of the ping message"}
    )


class PingConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        required=True,
        metadata={"description": "Connection identifier", "example": UUID4_EXAMPLE},
    )


@docs(tags=["trustping"], summary="Send a trust ping to a connection")
@request_schema(PingRequestSchema())
@response_schema(PingRequestResponseSchema(), 200, description="")
@tenant_authentication
async def connections_send_ping(request: web.BaseRequest):
    """Request handler for sending a trust ping to a connection.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    connection_id = request.match_info["conn_id"]
    outbound_handler = request["outbound_message_router"]
    body = await request.json()
    to = body.get("to")
    response_requested = body.get("response_requested")

    try:
        async with context.profile.session() as session:
            resolver = session.inject(DMPResolver)
            did_doc = await resolver.resolve(to)
    except Exception as err:
        raise web.HTTPNotFound(reason=str(err)) from err

    #if not connection.is_ready:
    #    raise web.HTTPBadRequest(reason=f"Connection {connection_id} not ready")

    #msg = Ping(did=did, response_requested=response_requested)
    #await outbound_handler(msg, connection_id=connection_id)

    #return web.json_response({"thread_id": msg._thread_id})
    return web.json_response({"thread_id": "blah"})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes([web.post("/trust-ping/send-ping", connections_send_ping)])


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "trustping",
            "description": "Trust-ping over connection",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
