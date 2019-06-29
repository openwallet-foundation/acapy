"""Introduction service admin routes."""

import logging

from aiohttp import web
from aiohttp_apispec import docs

from .base_service import BaseIntroductionService

LOGGER = logging.getLogger(__name__)


@docs(
    tags=["introduction"],
    summary="Start an introduction between two connections",
    parameters=[
        {
            "name": "target_connection_id",
            "in": "query",
            "schema": {"type": "string"},
            "required": True,
        },
        {
            "name": "message",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
    ],
)
async def introduction_start(request: web.BaseRequest):
    """
    Request handler for starting an introduction.

    Args:
        request: aiohttp request object

    """
    LOGGER.info("Introduction requested")
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    init_connection_id = request.match_info["id"]
    target_connection_id = request.query.get("target_connection_id")
    message = request.query.get("message")

    service: BaseIntroductionService = await context.inject(
        BaseIntroductionService, required=False
    )
    if not service:
        raise web.HTTPForbidden()

    await service.start_introduction(
        init_connection_id, target_connection_id, message, outbound_handler
    )
    return web.json_response({})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [web.post("/connections/{id}/start-introduction", introduction_start)]
    )
