"""Action menu admin routes."""

import logging

from aiohttp import web
from aiohttp_apispec import docs, match_info_schema, request_schema, response_schema

from marshmallow import fields

from ....admin.request_context import AdminRequestContext
from ....connections.models.conn_record import ConnRecord
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import UUIDFour
from ....storage.error import StorageError, StorageNotFoundError

from .messages.menu import Menu, MenuSchema
from .messages.menu_request import MenuRequest
from .messages.perform import Perform
from .models.menu_option import MenuOptionSchema
from .util import MENU_RECORD_TYPE, retrieve_connection_menu, save_connection_menu

LOGGER = logging.getLogger(__name__)


class ActionMenuModulesResultSchema(OpenAPISchema):
    """Schema for the modules endpoint."""


class PerformRequestSchema(OpenAPISchema):
    """Request schema for performing a menu action."""

    name = fields.Str(description="Menu option name", example="Query")
    params = fields.Dict(
        description=("Input parameter values"),
        required=False,
        keys=fields.Str(example="parameter"),  # marshmallow/apispec v3.0 ignores
        values=fields.Str(example=UUIDFour.EXAMPLE),
    )


class MenuJsonSchema(OpenAPISchema):
    """Matches MenuSchema but without the inherited AgentMessage properties."""

    title = fields.Str(
        required=False,
        description="Menu title",
        example="My Menu",
    )
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


class SendMenuSchema(OpenAPISchema):
    """Request schema for sending a menu to a connection."""

    menu = fields.Nested(
        MenuJsonSchema(),
        required=True,
        description="Menu to send to connection",
    )


class MenuConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        description="Connection identifier", required=True, example=UUIDFour.EXAMPLE
    )


class ActionMenuFetchResultSchema(OpenAPISchema):
    """Result schema for action-menu fetch."""

    result = fields.Nested(MenuSchema, description="Action menu")


@docs(
    tags=["action-menu"], summary="Close the active menu associated with a connection"
)
@match_info_schema(MenuConnIdMatchInfoSchema())
@response_schema(ActionMenuModulesResultSchema(), 200, description="")
async def actionmenu_close(request: web.BaseRequest):
    """
    Request handler for closing the menu associated with a connection.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    connection_id = request.match_info["conn_id"]

    menu = await retrieve_connection_menu(connection_id, context)
    if not menu:
        raise web.HTTPNotFound(
            reason=f"No {MENU_RECORD_TYPE} record found for connection {connection_id}"
        )

    try:
        await save_connection_menu(None, connection_id, context)
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


@docs(tags=["action-menu"], summary="Fetch the active menu")
@match_info_schema(MenuConnIdMatchInfoSchema())
@response_schema(ActionMenuFetchResultSchema(), 200, description="")
async def actionmenu_fetch(request: web.BaseRequest):
    """
    Request handler for fetching the previously-received menu for a connection.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    connection_id = request.match_info["conn_id"]

    menu = await retrieve_connection_menu(connection_id, context)
    result = {"result": menu.serialize() if menu else None}
    return web.json_response(result)


@docs(tags=["action-menu"], summary="Perform an action associated with the active menu")
@match_info_schema(MenuConnIdMatchInfoSchema())
@request_schema(PerformRequestSchema())
@response_schema(ActionMenuModulesResultSchema(), 200, description="")
async def actionmenu_perform(request: web.BaseRequest):
    """
    Request handler for performing a menu action.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    connection_id = request.match_info["conn_id"]
    outbound_handler = request["outbound_message_router"]
    params = await request.json()

    try:
        async with context.profile.session() as session:
            connection = await ConnRecord.retrieve_by_id(session, connection_id)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    if connection.is_ready:
        msg = Perform(name=params["name"], params=params.get("params"))
        await outbound_handler(msg, connection_id=connection_id)
        return web.json_response({})

    raise web.HTTPForbidden(reason=f"Connection {connection_id} not ready")


@docs(tags=["action-menu"], summary="Request the active menu")
@match_info_schema(MenuConnIdMatchInfoSchema())
@response_schema(ActionMenuModulesResultSchema(), 200, description="")
async def actionmenu_request(request: web.BaseRequest):
    """
    Request handler for requesting a menu from the connection target.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    connection_id = request.match_info["conn_id"]
    outbound_handler = request["outbound_message_router"]

    try:
        async with context.profile.session() as session:
            connection = await ConnRecord.retrieve_by_id(session, connection_id)
    except StorageNotFoundError as err:
        LOGGER.debug("Connection not found for action menu request: %s", connection_id)
        raise web.HTTPNotFound(reason=err.roll_up) from err

    if connection.is_ready:
        msg = MenuRequest()
        await outbound_handler(msg, connection_id=connection_id)
        return web.json_response({})

    raise web.HTTPForbidden(reason=f"Connection {connection_id} not ready")


@docs(tags=["action-menu"], summary="Send an action menu to a connection")
@match_info_schema(MenuConnIdMatchInfoSchema())
@request_schema(SendMenuSchema())
@response_schema(ActionMenuModulesResultSchema(), 200, description="")
async def actionmenu_send(request: web.BaseRequest):
    """
    Request handler for requesting a menu from the connection target.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    connection_id = request.match_info["conn_id"]
    outbound_handler = request["outbound_message_router"]
    menu_json = await request.json()
    LOGGER.debug("Received send-menu request: %s %s", connection_id, menu_json)
    try:
        msg = Menu.deserialize(menu_json["menu"])
    except BaseModelError as err:
        LOGGER.exception("Exception deserializing menu: %s", err.roll_up)
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    try:
        async with context.profile.session() as session:
            connection = await ConnRecord.retrieve_by_id(session, connection_id)
    except StorageNotFoundError as err:
        LOGGER.debug(
            "Connection not found for action menu send request: %s", connection_id
        )
        raise web.HTTPNotFound(reason=err.roll_up) from err

    if connection.is_ready:
        await outbound_handler(msg, connection_id=connection_id)
        return web.json_response({})

    raise web.HTTPForbidden(reason=f"Connection {connection_id} not ready")


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.post("/action-menu/{conn_id}/close", actionmenu_close),
            web.post("/action-menu/{conn_id}/fetch", actionmenu_fetch),
            web.post("/action-menu/{conn_id}/perform", actionmenu_perform),
            web.post("/action-menu/{conn_id}/request", actionmenu_request),
            web.post("/action-menu/{conn_id}/send-menu", actionmenu_send),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {"name": "action-menu", "description": "Menu interaction over connection"}
    )
