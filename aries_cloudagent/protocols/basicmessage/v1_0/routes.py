"""Basic message admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, match_info_schema, request_schema

from marshmallow import fields

from ....admin.request_context import AdminRequestContext
from ....connections.models.conn_record import ConnRecord
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import UUIDFour
from ....storage.error import StorageNotFoundError

from .message_types import SPEC_URI
from .messages.basicmessage import BasicMessage


class SendMessageSchema(OpenAPISchema):
    """Request schema for sending a message."""

    content = fields.Str(description="Message content", example="Hello")


class ConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        description="Connection identifier", required=True, example=UUIDFour.EXAMPLE
    )


@docs(tags=["basicmessage"], summary="Send a basic message to a connection")
@match_info_schema(ConnIdMatchInfoSchema())
@request_schema(SendMessageSchema())
async def connections_send_message(request: web.BaseRequest):
    """
    Request handler for sending a basic message to a connection.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    connection_id = request.match_info["conn_id"]
    outbound_handler = request.app["outbound_message_router"]
    params = await request.json()

    try:
        connection = await ConnRecord.retrieve_by_id(context, connection_id)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    if connection.is_ready:
        msg = BasicMessage(content=params["content"])
        await outbound_handler(msg, connection_id=connection_id)

    return web.json_response({})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [web.post("/connections/{conn_id}/send-message", connections_send_message)]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "basicmessage",
            "description": "Simple messaging",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
