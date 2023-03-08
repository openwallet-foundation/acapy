import logging

from ...config.injection_context import InjectionContext
from ...config.provider import ClassProvider

from ..anoncreds.anoncreds_registry import AnonCredsRegistry

LOGGER = logging.getLogger(__name__)


async def setup(context: InjectionContext):
    """Set up default resolvers."""
    registry = context.inject_or(AnonCredsRegistry)
    if not registry:
        LOGGER.warning("No DID Resolver instance found in context")
        return

    indy_registry = ClassProvider(
        "aries_cloudagent.anoncreds.did_indy_registry.v1_0.did_indy_registry.DIDIndyRegistry"
    ).provide(context.settings, context.injector)
    await indy_registry.setup(context)
    registry.register_registry(indy_registry)

    web_registry = ClassProvider(
        "aries_cloudagent.anoncreds.did_web_registry.v1_0.did_web_registry.DIDWebRegistry"
    ).provide(context.settings, context.injector)
    await web_registry.setup(context)
    registry.register_registry(web_registry)

    # TODO: add context.settings
