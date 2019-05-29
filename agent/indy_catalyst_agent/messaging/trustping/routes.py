"""Trust ping admin routes."""

from aiohttp import web
from aiohttp_apispec import docs

from ..connections.manager import ConnectionManager
from ..connections.models.connection_record import ConnectionRecord
from .messages.ping import Ping
from ...storage.error import StorageNotFoundError


@docs(tags=["trustping"], summary="Send a trust ping to a connection")
async def connections_send_ping(request: web.BaseRequest):
    """
    Request handler for sending a trust ping to a connection.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    connection_id = request.match_info["id"]
    connection_mgr = ConnectionManager(context)
    outbound_handler = request.app["outbound_message_router"]

    try:
        connection = await ConnectionRecord.retrieve_by_id(context, connection_id)
    except StorageNotFoundError:
        return web.HTTPNotFound()

    if connection.state == "active":
        msg = Ping()
        target = await connection_mgr.get_connection_target(connection)
        await outbound_handler(context, msg, target)

        await connection.log_activity(context, "ping", connection.DIRECTION_SENT)

    return web.HTTPOk()


async def register(app: web.Application):
    """Register routes."""

    app.add_routes([web.post("/connections/{id}/send-ping", connections_send_ping)])
