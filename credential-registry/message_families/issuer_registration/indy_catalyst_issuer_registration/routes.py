"""Issuer registration admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema

from marshmallow import fields, Schema

from indy_catalyst_agent.messaging.connections.models.connection_record import (
    ConnectionRecord,
)
from indy_catalyst_agent.storage.error import StorageNotFoundError

from .messages.register import IssuerRegistration


@docs(tags=["issuer_registration"], summary="Send an issuer registration to a target")
@request_schema(SendMessageSchema())
async def issuer_registration_send(request: web.BaseRequest):
    """
    Request handler for sending an issuer registration message to a connection.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    connection_id = request.match_info["id"]
    outbound_handler = request.app["outbound_message_router"]
    params = await request.body()

    try:
        connection = await ConnectionRecord.retrieve_by_id(context, connection_id)
    except StorageNotFoundError:
        return web.HTTPNotFound()

    if connection.is_active:
        msg = IssuerRegistration(**body)
        await outbound_handler(msg, connection_id=connection_id)

        await connection.log_activity(
            context, "issuer_registration", connection.DIRECTION_SENT
        )

    return web.HTTPOk()


async def register(app: web.Application):
    """Register routes."""
    app.add_routes([web.get("/issuer_registration/send", issuer_registration_send)])
