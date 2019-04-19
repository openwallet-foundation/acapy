"""Introduction service admin routes."""

from aiohttp import web
from aiohttp_apispec import docs

from .base_service import BaseIntroductionService


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
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    init_connection_id = request.match_info["id"]
    target_connection_id = request.query["target_connection_id"]
    message = request.query.get("message")

    service: BaseIntroductionService = await context.service_factory.resolve_service(
        "introduction"
    )
    if service:
        await service.start_introduction(
            init_connection_id, target_connection_id, message, outbound_handler
        )
        return web.HTTPOk()

    return web.HTTPForbidden()


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [web.post("/connections/{id}/start-introduction", introduction_start)]
    )
