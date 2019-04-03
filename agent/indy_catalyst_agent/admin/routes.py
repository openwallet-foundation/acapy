"""Register default routes."""

from aiohttp import web

from ..messaging.connections.routes import register as register_connections
from ..messaging.discovery.routes import register as register_discovery
from ..messaging.basicmessage.routes import register as register_basicmessages
from ..messaging.trustping.routes import register as register_trustping


async def register_module_routes(app: web.Application):
    """
    Register default routes with the webserver.

    Eventually this should use dynamic registration based on the
    selected message families.
    """
    await register_connections(app)
    await register_discovery(app)
    await register_basicmessages(app)
    await register_trustping(app)
