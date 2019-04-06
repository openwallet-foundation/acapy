"""Trust ping admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema

from marshmallow import fields, Schema

from ..connections.manager import ConnectionManager
from ..connections.models.connection_record import ConnectionRecord
from .messages.menu_request import MenuRequest
from .messages.perform import Perform
from ...storage.error import StorageNotFoundError


class PerformRequestSchema(Schema):
    """Request schema for performing a menu action."""

    name = fields.Str()
    params = fields.Dict(required=False)


@docs(
    tags=["action-menu"], summary="Close the active menu associated with a connection"
)
async def actionmenu_close(request: web.BaseRequest):
    """
    Request handler for closing the menu associated with a connection.

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

    if connection.state == "active" and connection.active_menu:
        connection.active_menu = None
        await connection.save(context.storage)

    return web.HTTPOk()


@docs(tags=["action-menu"], summary="Fetch the active menu")
async def actionmenu_request(request: web.BaseRequest):
    """
    Request handler for fetching a menu from the connection target.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    connection_id = request.match_info["id"]
    connection_mgr = ConnectionManager(context)
    outbound_handler = request.app["outbound_message_router"]

    try:
        connection = await ConnectionRecord.retrieve_by_id(
            context.storage, connection_id
        )
    except StorageNotFoundError:
        return web.HTTPNotFound()

    if connection.state == "active":
        msg = MenuRequest()
        target = await connection_mgr.get_connection_target(connection)
        await outbound_handler(msg, target)

    return web.HTTPForbidden()


@docs(tags=["action-menu"], summary="Perform an action associated with the active menu")
@request_schema(PerformRequestSchema)
async def actionmenu_perform(request: web.BaseRequest):
    """
    Request handler for performing a menu action.

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

    if connection.state == "active" and connection.active_menu:
        msg = Perform(name=params["name"], params=params.get("params"))
        target = await connection_mgr.get_connection_target(connection)
        await outbound_handler(msg, target)
        return web.HTTPOk()

    return web.HTTPForbidden()


async def register(app: web.Application):
    """Register routes."""

    app.add_routes([web.post("/action-menu/{id}/close", actionmenu_close)])
    app.add_routes([web.post("/action-menu/{id}/perform", actionmenu_perform)])
    app.add_routes([web.post("/action-menu/{id}/request", actionmenu_request)])
