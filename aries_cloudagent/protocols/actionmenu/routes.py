"""Action menu admin routes."""

import logging

from aiohttp import web
from aiohttp_apispec import docs, request_schema

from marshmallow import fields, Schema

from ...connections.models.connection_record import ConnectionRecord
from ...messaging.valid import UUIDFour
from ...storage.error import StorageNotFoundError

from .messages.menu import Menu
from .messages.menu_request import MenuRequest
from .messages.perform import Perform
from .models.menu_option import MenuOptionSchema
from .util import retrieve_connection_menu, save_connection_menu

LOGGER = logging.getLogger(__name__)


class PerformRequestSchema(Schema):
    """Request schema for performing a menu action."""

    name = fields.Str(description="Menu option name", example="Query")
    params = fields.Dict(
        description=("Input parameter values"),
        required=False,
        keys=fields.Str(example="parameter"),  # marshmallow/apispec v3.0 ignores
        values=fields.Str(example=UUIDFour.EXAMPLE),
    )


class MenuJsonSchema(Schema):
    """Matches MenuSchema but without the inherited AgentMessage properties."""

    title = fields.Str(required=False, description="Menu title", example="My Menu",)
    description = fields.Str(
        required=False,
        description="Introductory text for the menu",
        example="User preferences for window settings",
    )
    errormsg = fields.Str(
        required=False,
        description="Optional error message to display in menu header",
        example="Error: item not present",
    )
    options = fields.List(
        fields.Nested(MenuOptionSchema),
        required=True,
        description="List of menu options",
    )


class SendMenuSchema(Schema):
    """Request schema for sending a menu to a connection."""

    menu = fields.Nested(
        MenuJsonSchema(), required=True, description="Menu to send to connection",
    )


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

    menu = await retrieve_connection_menu(connection_id, context)
    if not menu:
        raise web.HTTPNotFound()

    await save_connection_menu(None, connection_id, context)
    return web.json_response({})


@docs(tags=["action-menu"], summary="Fetch the active menu")
async def actionmenu_fetch(request: web.BaseRequest):
    """
    Request handler for fetching the previously-received menu for a connection.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    connection_id = request.match_info["id"]

    menu = await retrieve_connection_menu(connection_id, context)
    result = {"result": menu.serialize() if menu else None}
    return web.json_response(result)


@docs(tags=["action-menu"], summary="Perform an action associated with the active menu")
@request_schema(PerformRequestSchema())
async def actionmenu_perform(request: web.BaseRequest):
    """
    Request handler for performing a menu action.

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
        msg = Perform(name=params["name"], params=params.get("params"))
        await outbound_handler(msg, connection_id=connection_id)
        return web.json_response({})

    raise web.HTTPForbidden()


@docs(tags=["action-menu"], summary="Request the active menu")
async def actionmenu_request(request: web.BaseRequest):
    """
    Request handler for requesting a menu from the connection target.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    connection_id = request.match_info["id"]
    outbound_handler = request.app["outbound_message_router"]

    try:
        connection = await ConnectionRecord.retrieve_by_id(context, connection_id)
    except StorageNotFoundError:
        LOGGER.debug("Connection not found for action menu request: %s", connection_id)
        raise web.HTTPNotFound()

    if connection.is_ready:
        msg = MenuRequest()
        await outbound_handler(msg, connection_id=connection_id)
        return web.json_response({})

    raise web.HTTPForbidden()


@docs(tags=["action-menu"], summary="Send an action menu to a connection")
@request_schema(SendMenuSchema())
async def actionmenu_send(request: web.BaseRequest):
    """
    Request handler for requesting a menu from the connection target.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    connection_id = request.match_info["id"]
    outbound_handler = request.app["outbound_message_router"]
    menu_json = await request.json()
    LOGGER.debug("Received send-menu request: %s %s", connection_id, menu_json)
    try:
        msg = Menu.deserialize(menu_json["menu"])
    except Exception:
        LOGGER.exception("Exception deserializing menu")
        raise

    try:
        connection = await ConnectionRecord.retrieve_by_id(context, connection_id)
    except StorageNotFoundError:
        LOGGER.debug(
            "Connection not found for action menu send request: %s", connection_id
        )
        raise web.HTTPNotFound()

    if connection.is_ready:
        await outbound_handler(msg, connection_id=connection_id)
        return web.json_response({})

    raise web.HTTPForbidden()


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/action-menu/{id}/close", actionmenu_close),
            web.post("/action-menu/{id}/fetch", actionmenu_fetch),
            web.post("/action-menu/{id}/perform", actionmenu_perform),
            web.post("/action-menu/{id}/request", actionmenu_request),
            web.post("/connections/{id}/send-menu", actionmenu_send),
        ]
    )
