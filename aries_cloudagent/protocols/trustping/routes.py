"""Trust ping admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema

from marshmallow import fields, Schema

from ...connections.models.connection_record import ConnectionRecord
from ...storage.error import StorageNotFoundError

from .messages.ping import Ping


class PingRequestSchema(Schema):
    """Request schema for performing a ping."""

    comment = fields.Str(required=False, description="Comment for the ping message")


class PingRequestResponseSchema(Schema):
    """Request schema for performing a ping."""

    thread_id = fields.Str(required=False, description="Thread ID of the ping message")


@docs(tags=["trustping"], summary="Send a trust ping to a connection")
@request_schema(PingRequestSchema())
@response_schema(PingRequestResponseSchema(), 200)
async def connections_send_ping(request: web.BaseRequest):
    """
    Request handler for sending a trust ping to a connection.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    connection_id = request.match_info["id"]
    outbound_handler = request.app["outbound_message_router"]
    body = await request.json()
    comment = body.get("comment")

    try:
        connection = await ConnectionRecord.retrieve_by_id(context, connection_id)
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    if not connection.is_ready:
        raise web.HTTPBadRequest()

    msg = Ping(comment=comment)
    await outbound_handler(msg, connection_id=connection_id)

    return web.json_response({"thread_id": msg._thread_id})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes([web.post("/connections/{id}/send-ping", connections_send_ping)])
