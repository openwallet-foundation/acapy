"""All issue_credential routes."""

from aiohttp import web

from .v1_0.routes import register as v10_register
from .v1_1.routes import register as v11_register


async def register(app: web.Application):
    """Register routes."""

    await v10_register(app)
    await v11_register(app)

__all__ = ("register",)
