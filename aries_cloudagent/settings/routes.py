"""Settings routes."""

import logging

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema

from marshmallow import fields

from ..admin.request_context import AdminRequestContext
from ..core.error import BaseError
from ..core.profile import Profile
from ..messaging.models.openapi import OpenAPISchema
from ..multitenant.admin.routes import (
    ACAPY_LIFECYCLE_CONFIG_FLAG_ARGS_MAP,
    get_extra_settings_dict_per_tenant,
)
from ..multitenant.base import BaseMultitenantManager

LOGGER = logging.getLogger(__name__)


class UpdateProfileSettingsSchema(OpenAPISchema):
    """Schema to update profile settings."""

    extra_settings = fields.Dict(
        required=False,
        metadata={
            "description": "Agent config key-value pairs",
            "example": {
                "log-level": "INFO",
                "ACAPY_INVITE_PUBLIC": True,
                "public-invites": False,
            },
        },
    )


class ProfileSettingsSchema(OpenAPISchema):
    """Profile settings response schema."""

    settings = fields.Dict(
        metadata={
            "description": "Profile settings dict",
            "example": {
                "log.level": "INFO",
                "debug.invite_public": True,
                "public_invites": False,
            },
        }
    )


def _get_filtered_settings_dict(wallet_settings: dict):
    """Get filtered settings dict to display."""
    filter_param_list = list(ACAPY_LIFECYCLE_CONFIG_FLAG_ARGS_MAP.values())
    filter_param_list.append("endorser.author")
    filter_param_list.append("endorser.endorser")
    settings_dict = {}
    for param in filter_param_list:
        if param in wallet_settings:
            settings_dict[param] = wallet_settings.get(param)
    return settings_dict


def _get_multitenant_settings_dict(
    profile_settings: dict,
    wallet_settings: dict,
):
    """Get filtered settings dict when multitenant manager is present."""
    all_settings = {**profile_settings, **wallet_settings}
    settings_dict = _get_filtered_settings_dict(all_settings)
    return settings_dict


def _get_settings_dict(
    profile: Profile,
):
    """Get filtered settings dict when multitenant manager is not present."""
    settings_dict = _get_filtered_settings_dict((profile.settings).to_dict())
    return settings_dict


@docs(
    tags=["settings"],
    summary="Update configurable settings associated with the profile.",
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
    root_profile = context.root_profile or context.profile
    try:
        body = await request.json()
        extra_settings = get_extra_settings_dict_per_tenant(
            body.get("extra_settings") or {}
        )
        async with root_profile.session() as session:
            multitenant_mgr = session.inject_or(BaseMultitenantManager)
            if multitenant_mgr:
                wallet_id = context.metadata.get("wallet_id")
                wallet_key = context.metadata.get("wallet_key")
                wallet_record = await multitenant_mgr.update_wallet(
                    wallet_id, extra_settings
                )
                wallet_record, profile = await multitenant_mgr.get_wallet_and_profile(
                    root_profile.context, wallet_id, wallet_key
                )
                settings_dict = _get_multitenant_settings_dict(
                    profile_settings=profile.settings.to_dict(),
                    wallet_settings=wallet_record.settings,
                )
            else:
                root_profile.context.update_settings(extra_settings)
                settings_dict = _get_settings_dict(profile=root_profile)
    except BaseError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response(settings_dict)


@docs(
    tags=["settings"],
    summary="Get the configurable settings associated with the profile.",
)
@response_schema(ProfileSettingsSchema(), 200, description="")
async def get_profile_settings(request: web.BaseRequest):
    """
    Request handler for getting setting associated with profile.

    Args:
        request: aiohttp request object
    """
    context: AdminRequestContext = request["context"]
    root_profile = context.root_profile or context.profile
    try:
        async with root_profile.session() as session:
            multitenant_mgr = session.inject_or(BaseMultitenantManager)
            if multitenant_mgr:
                wallet_id = context.metadata.get("wallet_id")
                wallet_key = context.metadata.get("wallet_key")
                wallet_record, profile = await multitenant_mgr.get_wallet_and_profile(
                    root_profile.context, wallet_id, wallet_key
                )
                settings_dict = _get_multitenant_settings_dict(
                    profile_settings=profile.settings.to_dict(),
                    wallet_settings=wallet_record.settings,
                )
            else:
                settings_dict = _get_settings_dict(profile=root_profile)
    except BaseError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return web.json_response(settings_dict)


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
