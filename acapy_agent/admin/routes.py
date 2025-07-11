"""Admin server routes."""

import re

from aiohttp import web
from aiohttp_apispec import docs, response_schema
from marshmallow import fields

from ..core.plugin_registry import PluginRegistry
from ..messaging.models.openapi import OpenAPISchema
from ..utils.stats import Collector
from ..version import __version__
from .decorators.auth import admin_authentication


class AdminModulesSchema(OpenAPISchema):
    """Schema for the modules endpoint."""

    result = fields.List(
        fields.Str(metadata={"description": "admin module"}),
        metadata={"description": "List of admin modules"},
    )


class AdminConfigSchema(OpenAPISchema):
    """Schema for the config endpoint."""

    config = fields.Dict(
        required=True, metadata={"description": "Configuration settings"}
    )


class AdminStatusSchema(OpenAPISchema):
    """Schema for the status endpoint."""

    version = fields.Str(metadata={"description": "Version code"})
    label = fields.Str(allow_none=True, metadata={"description": "Default label"})
    timing = fields.Dict(required=False, metadata={"description": "Timing results"})
    conductor = fields.Dict(
        required=False, metadata={"description": "Conductor statistics"}
    )


class AdminResetSchema(OpenAPISchema):
    """Schema for the reset endpoint."""


class AdminStatusLivelinessSchema(OpenAPISchema):
    """Schema for the liveliness endpoint."""

    alive = fields.Boolean(metadata={"description": "Liveliness status", "example": True})


class AdminStatusReadinessSchema(OpenAPISchema):
    """Schema for the readiness endpoint."""

    ready = fields.Boolean(metadata={"description": "Readiness status", "example": True})


class AdminShutdownSchema(OpenAPISchema):
    """Response schema for admin Module."""


@docs(tags=["server"], summary="Fetch the list of loaded plugins")
@response_schema(AdminModulesSchema(), 200, description="")
@admin_authentication
async def plugins_handler(request: web.BaseRequest):
    """Request handler for the loaded plugins list.

    Args:
        request: aiohttp request object

    Returns:
        The module list response

    """
    registry = request.app["context"].inject_or(PluginRegistry)
    plugins = registry and sorted(registry.plugin_names) or []
    return web.json_response({"result": plugins})


@docs(tags=["server"], summary="Fetch the server configuration")
@response_schema(AdminConfigSchema(), 200, description="")
@admin_authentication
async def config_handler(request: web.BaseRequest):
    """Request handler for the server configuration.

    Args:
        request: aiohttp request object

    Returns:
        The web response

    """
    config = {
        k: (
            request.app["context"].settings[k]
            if (isinstance(request.app["context"].settings[k], (str, int)))
            else request.app["context"].settings[k].copy()
        )
        for k in request.app["context"].settings
        if k
        not in [
            "admin.admin_api_key",
            "multitenant.jwt_secret",
            "wallet.key",
            "wallet.rekey",
            "wallet.seed",
            "wallet.storage_creds",
        ]
    }
    for index in range(len(config.get("admin.webhook_urls", []))):
        config["admin.webhook_urls"][index] = re.sub(
            r"#.*",
            "",
            config["admin.webhook_urls"][index],
        )

    return web.json_response({"config": config})


@docs(tags=["server"], summary="Fetch the server status")
@response_schema(AdminStatusSchema(), 200, description="")
@admin_authentication
async def status_handler(request: web.BaseRequest):
    """Request handler for the server status information.

    Args:
        request: aiohttp request object

    Returns:
        The web response

    """
    status = {"version": __version__}
    status["label"] = request.app["context"].settings.get("default_label")
    collector = request.app["context"].inject_or(Collector)
    if collector:
        status["timing"] = collector.results
    if request.app["conductor_stats"]:
        status["conductor"] = await request.app["conductor_stats"]()
    return web.json_response(status)


@docs(tags=["server"], summary="Reset statistics")
@response_schema(AdminResetSchema(), 200, description="")
@admin_authentication
async def status_reset_handler(request: web.BaseRequest):
    """Request handler for resetting the timing statistics.

    Args:
        request: aiohttp request object

    Returns:
        The web response

    """
    collector = request.app["context"].inject_or(Collector)
    if collector:
        collector.reset()
    return web.json_response({})


async def redirect_handler(request: web.BaseRequest):
    """Perform redirect to documentation."""
    raise web.HTTPFound("/api/doc")


@docs(tags=["server"], summary="Liveliness check")
@response_schema(AdminStatusLivelinessSchema(), 200, description="")
async def liveliness_handler(request: web.BaseRequest):
    """Request handler for liveliness check.

    Args:
        request: aiohttp request object

    Returns:
        The web response, always indicating True

    """
    app_live = request.app._state["alive"]
    if app_live:
        return web.json_response({"alive": app_live})
    else:
        raise web.HTTPServiceUnavailable(reason="Service not available")


@docs(tags=["server"], summary="Readiness check")
@response_schema(AdminStatusReadinessSchema(), 200, description="")
async def readiness_handler(request: web.BaseRequest):
    """Request handler for liveliness check.

    Args:
        request: aiohttp request object

    Returns:
        The web response, indicating readiness for further calls

    """
    app_ready = request.app._state["ready"] and request.app._state["alive"]
    if app_ready:
        return web.json_response({"ready": app_ready})
    else:
        raise web.HTTPServiceUnavailable(reason="Service not ready")


@docs(tags=["server"], summary="Shut down server")
@response_schema(AdminShutdownSchema(), description="")
@admin_authentication
async def shutdown_handler(request: web.BaseRequest):
    """Request handler for server shutdown.

    Args:
        request: aiohttp request object

    Returns:
        The web response (empty production)

    """
    request.app._state["ready"] = False
    await request.app["conductor_stop"]()
    return web.json_response({})
