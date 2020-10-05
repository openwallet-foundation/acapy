"""DID exchange admin routes."""

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)
from marshmallow import fields, validate

from ....messaging.models.base import BaseModelError, OpenAPISchema
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import ENDPOINT

from .manager import DIDExManager
from .models.didexchange import DIDExRecord


class SendRequestRequestSchema(OpenAPISchema):
    """Request schema for HTTP request to send DID exchange request."""

    label = fields.Str(description="Label for DID exchange", required=False)
    endpoint = fields.Str(
        description="Endpoint to contact for DID exchange",
        **ENDPOINT,
    )
    # TODO - allow for public DID specification?


@docs(tags=["did-exchange"], summary="Send DID exchange request")
@request_schema(SendRequestRequestSchema())
async def send_request(request: web.BaseRequest):
    """
    Request handler to send DID exchange request.

    Args:
        request: aiohttp request object

    Returns:
        The connection list response

    """
    context = request.app["request_context"]

    body = await request.json()
    endpoint = body.get("endpoint")
    label = body.get("label")

    manager = DIDExManager(context)

    try:
        await manager.send_request(endpoint, label)
    except StorageError, ValueError as err:  # TODO find possible exceptions for here
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes([web.post("/did-exchange/send-request", send_request)])

