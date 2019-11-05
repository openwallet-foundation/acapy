"""Register default routes."""

from aiohttp import web

from ..classloader import ClassLoader, ModuleLoadError

from ..messaging.present_proof.v1_0.routes import register as register_v10_present_proof
from ..messaging.schemas.routes import register as register_schemas
from ..messaging.credential_definitions.routes import (
    register as register_credential_definitions,
)
from ..ledger.routes import register as register_ledger
from ..wallet.routes import register as register_wallet


async def register_module_routes(app: web.Application):
    """
    Register default routes with the webserver.

    Eventually this should use dynamic registration based on the
    currently-selected message families.
    """
    await register_schemas(app)
    await register_credential_definitions(app)
    await register_v10_present_proof(app)
    await register_wallet(app)
    await register_ledger(app)

    packages = ClassLoader.scan_subpackages("aries_cloudagent.protocols")
    for pkg in packages:
        try:
            mod = ClassLoader.load_module(pkg + ".routes")
            await mod.register(app)
        except ModuleLoadError:
            pass
