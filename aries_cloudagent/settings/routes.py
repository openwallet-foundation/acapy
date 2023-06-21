"""Settings routes."""

import logging

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import fields

from ..admin.request_context import AdminRequestContext
from ..core.error import BaseError
from ..messaging.models.openapi import OpenAPISchema
from ..multitenant.admin.routes import get_extra_settings_dict_per_tenant

LOGGER = logging.getLogger(__name__)


class UpdateProfileSettingsSchema(OpenAPISchema):
    """Schema to update profile settings."""

    extra_settings = fields.Dict(
        description="Agent config key-value pairs",
        required=False,
        example={
            "log_level": "INFO",
            "ACAPY_INVITE_PUBLIC": True,
            "public_invites": False,
        },
    )


class ProfileSettingsSchema(OpenAPISchema):
    """Profile settings response schema."""

    settings = fields.Dict(
        description="Profile settings dict",
        example={
            "log.level": "INFO",
            "debug.invite_public": True,
            "public_invites": False,
        },
    )


@docs(
    tags=["settings"],
    summary="Update settings or config associated with the profile.",
)
@request_schema(UpdateProfileSettingsSchema())
@response_schema(ProfileSettingsSchema(), 200, description="")
async def update_profile_settings(request: web.BaseRequest):
    """
    Request handler for updating setting associated with profile.

    Args:
        request: aiohttp request object
    """
    context: AdminRequestContext = request["context"]
    try:
        body = await request.json()
        extra_setting = get_extra_settings_dict_per_tenant(
            body.get("extra_settings") or {}
        )
        context.profile.settings.update(extra_setting)
        result = context.profile.settings
    except BaseError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response(result.to_dict())


@docs(
    tags=["settings"],
    summary="Get the settings or config associated with the profile.",
)
@response_schema(ProfileSettingsSchema(), 200, description="")
async def get_profile_settings(request: web.BaseRequest):
    """
    Request handler for getting setting associated with profile.

    Args:
        request: aiohttp request object
    """
    context: AdminRequestContext = request["context"]

    try:
        result = context.profile.settings
    except BaseError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response(result.to_dict())


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.put("/settings", update_profile_settings),
            web.get("/settings", get_profile_settings, allow_head=False),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "settings",
            "description": "Agent settings interface.",
        }
    )
