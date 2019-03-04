"""Register default routes."""

from aiohttp import web

from ..messaging.connections.routes import register as register_connections


async def register_module_routes(app: web.Application):
    """
    Register default routes with the webserver.

    Eventually this should use dynamic registration based on the
    selected message families.
    """
    await register_connections(app)
