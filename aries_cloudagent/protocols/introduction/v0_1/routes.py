"""Introduction service admin routes."""

import logging
from typing import Optional

from aiohttp import web
from aiohttp_apispec import docs, match_info_schema, querystring_schema, response_schema

from marshmallow import fields

from ....admin.request_context import AdminRequestContext
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import UUID4_EXAMPLE
from ....storage.error import StorageError
from .base_service import BaseIntroductionService, IntroductionError

LOGGER = logging.getLogger(__name__)


class IntroModuleResponseSchema(OpenAPISchema):
    """Response schema for Introduction Module."""


class IntroStartQueryStringSchema(OpenAPISchema):
    """Query string parameters for request to start introduction."""

    target_connection_id = fields.Str(
        required=True,
        metadata={
            "description": "Target connection identifier",
            "example": UUID4_EXAMPLE,
        },
    )
    message = fields.Str(
        required=False,
        metadata={"description": "Message", "example": "Allow me to introduce ..."},
    )


class IntroConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        required=True,
        metadata={"description": "Connection identifier", "example": UUID4_EXAMPLE},
    )


@docs(
    tags=["introduction"],
    summary="Start an introduction between two connections",
)
@match_info_schema(IntroConnIdMatchInfoSchema())
@querystring_schema(IntroStartQueryStringSchema())
@response_schema(IntroModuleResponseSchema, description="")
async def introduction_start(request: web.BaseRequest):
    """
    Request handler for starting an introduction.

    Args:
        request: aiohttp request object

    """
    LOGGER.info("Introduction requested")
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]
    init_connection_id = request.match_info["conn_id"]
    target_connection_id = request.query.get("target_connection_id")
    message = request.query.get("message")

    service: Optional[BaseIntroductionService] = context.inject_or(
        BaseIntroductionService
    )
    if not service:
        raise web.HTTPForbidden(reason="Introduction service not available")

    try:
        async with context.profile.session() as session:
            await service.start_introduction(
                init_connection_id,
                target_connection_id,
                message,
                session,
                outbound_handler,
            )
    except (IntroductionError, StorageError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [web.post("/connections/{conn_id}/start-introduction", introduction_start)]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {"name": "introduction", "description": "Introduction of known parties"}
    )
