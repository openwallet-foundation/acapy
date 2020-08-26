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


@docs(tags=["did-exchange"], summary="Fetch all credential exchange records")
async def send_request(request: web.BaseRequest):
    """
    Request handler for searching connection records.

    Args:
        request: aiohttp request object

    Returns:
        The connection list response

    """
    context = request.app["request_context"]

    try:
        records = await V10CredentialExchange.query(context, tag_filter, post_filter)
        results = [record.serialize() for record in records]
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"results": results})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes([web.post("/did-exchange/send-request", send_request)])
