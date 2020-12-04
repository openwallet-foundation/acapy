"""Trust ping admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, match_info_schema, request_schema, response_schema

from marshmallow import fields

from ....admin.request_context import AdminRequestContext
from ....connections.models.conn_record import ConnRecord
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import UUIDFour
from ....storage.error import StorageNotFoundError

from .message_types import SPEC_URI
from .messages.ping import Ping


class PingRequestSchema(OpenAPISchema):
    """Request schema for performing a ping."""

    comment = fields.Str(
        description="Comment for the ping message", required=False, allow_none=True
    )


class PingRequestResponseSchema(OpenAPISchema):
    """Request schema for performing a ping."""

    thread_id = fields.Str(required=False, description="Thread ID of the ping message")


class ConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        description="Connection identifier", required=True, example=UUIDFour.EXAMPLE
    )


@docs(tags=["trustping"], summary="Send a trust ping to a connection")
@match_info_schema(ConnIdMatchInfoSchema())
@request_schema(PingRequestSchema())
@response_schema(PingRequestResponseSchema(), 200)
async def connections_send_ping(request: web.BaseRequest):
    """
    Request handler for sending a trust ping to a connection.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    connection_id = request.match_info["conn_id"]
    outbound_handler = request.app["outbound_message_router"]
    body = await request.json()
    comment = body.get("comment")

    try:
        connection = await ConnRecord.retrieve_by_id(context, connection_id)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    if not connection.is_ready:
        raise web.HTTPBadRequest(reason=f"Connection {connection_id} not ready")

    msg = Ping(comment=comment)
    await outbound_handler(msg, connection_id=connection_id)

    return web.json_response({"thread_id": msg._thread_id})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [web.post("/connections/{conn_id}/send-ping", connections_send_ping)]
    )


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
