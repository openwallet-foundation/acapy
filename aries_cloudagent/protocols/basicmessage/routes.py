"""Basic message admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema

from marshmallow import fields, Schema

from ...connections.models.connection_record import ConnectionRecord
from ...storage.error import StorageNotFoundError

from .messages.basicmessage import BasicMessage


class SendMessageSchema(Schema):
    """Request schema for sending a message."""

    content = fields.Str(description="Message content", example="Hello")


@docs(tags=["basicmessage"], summary="Send a basic message to a connection")
@request_schema(SendMessageSchema())
async def connections_send_message(request: web.BaseRequest):
    """
    Request handler for sending a basic message to a connection.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    connection_id = request.match_info["id"]
    outbound_handler = request.app["outbound_message_router"]
    params = await request.json()

    try:
        connection = await ConnectionRecord.retrieve_by_id(context, connection_id)
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    if connection.is_ready:
        msg = BasicMessage(content=params["content"])
        await outbound_handler(msg, connection_id=connection_id)

    return web.json_response({})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [web.post("/connections/{id}/send-message", connections_send_message)]
    )
