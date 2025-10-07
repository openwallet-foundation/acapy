"""AnonCreds routes package."""

from aiohttp import web

from .cred_defs.routes import post_process_routes as post_process_cred_def_routes
from .cred_defs.routes import register as register_cred_def_routes
from .revocation.credentials.routes import (
    post_process_routes as post_process_credential_revocation_routes,
)
from .revocation.credentials.routes import (
    register as register_credential_revocation_routes,
)
from .revocation.lists.routes import register as register_revocation_list_routes
from .revocation.registry.routes import (
    post_process_routes as post_process_revocation_registry_routes,
)
from .revocation.registry.routes import register as register_revocation_registry_routes
from .revocation.tails.routes import register as register_tails_routes
from .schemas.routes import post_process_routes as post_process_schema_routes
from .schemas.routes import register as register_schema_routes


async def register(app: web.Application) -> None:
    """Register all AnonCreds routes."""
    # Register schema routes
    await register_schema_routes(app)

    # Register credential definition routes
    await register_cred_def_routes(app)

    # Register revocation routes
    await register_revocation_registry_routes(app)
    await register_revocation_list_routes(app)
    await register_tails_routes(app)
    await register_credential_revocation_routes(app)


def post_process_routes(app: web.Application) -> None:
    """Post-process all routes for swagger documentation."""
    # Post-process schema routes
    post_process_schema_routes(app)

    # Post-process credential definition routes
    post_process_cred_def_routes(app)

    # Post-process revocation routes
    post_process_revocation_registry_routes(app)
    post_process_credential_revocation_routes(app)
