"""Basic message admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema

from marshmallow import fields, Schema

from ..connections.manager import ConnectionManager
from ..connections.models.connection_record import ConnectionRecord
from .messages.basicmessage import BasicMessage
from ...storage.error import StorageNotFoundError


class SendMessageSchema(Schema):
    """Request schema for sending a message."""

    content = fields.Str()


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
    connection_mgr = ConnectionManager(context)
    outbound_handler = request.app["outbound_message_router"]
    params = await request.json()

    try:
        connection = await ConnectionRecord.retrieve_by_id(
            context.storage, connection_id
        )
    except StorageNotFoundError:
        return web.HTTPNotFound()

    if connection.state == "active":
        msg = BasicMessage(content=params["content"])
        target = await connection_mgr.get_connection_target(connection)
        await outbound_handler(msg, target)

        await connection.log_activity(
            context.storage,
            "message",
            connection.DIRECTION_SENT,
            {"content": params["content"]},
        )

    return web.HTTPOk()


@docs(tags=["basicmessage"], summary="Expire a copyable basicmessage")
async def connections_expire_message(request: web.BaseRequest):
    """
    Request handler for sending a basic message to a connection.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    connection_id = request.match_info["id"]

    try:
        connection = await ConnectionRecord.retrieve_by_id(
            context.storage, connection_id
        )
    except StorageNotFoundError:
        return web.HTTPNotFound()

    activity_id = request.match_info["activity_id"]
    activity = await connection.retrieve_activity(context.storage, activity_id)
    meta = activity.get("meta") or {}
    if meta.get("copy_invite"):
        meta["copied"] = 1
        await connection.update_activity_meta(context.storage, activity_id, meta)

    return web.HTTPOk()


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [web.post("/connections/{id}/send-message", connections_send_message)]
    )

    app.add_routes(
        [
            web.post(
                "/connections/{id}/expire-message/{activity_id}",
                connections_expire_message,
            )
        ]
    )
