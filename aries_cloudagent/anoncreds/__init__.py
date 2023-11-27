import logging

from ..config.injection_context import InjectionContext
from ..config.provider import ClassProvider

from .registry import AnonCredsRegistry

LOGGER = logging.getLogger(__name__)


async def setup(context: InjectionContext):
    """Set up default resolvers."""
    registry = context.inject_or(AnonCredsRegistry)
    if not registry:
        LOGGER.error("No AnonCredsRegistry instance found in context!!!")
        return

    indy_registry = ClassProvider(
        "aries_cloudagent.anoncreds.default.did_indy.registry.DIDIndyRegistry",
        # supported_identifiers=[],
        # method_name="did:indy",
    ).provide(context.settings, context.injector)
    await indy_registry.setup(context)
    registry.register(indy_registry)

    web_registry = ClassProvider(
        "aries_cloudagent.anoncreds.default.did_web.registry.DIDWebRegistry",
        # supported_identifiers=[],
        # method_name="did:web",
    ).provide(context.settings, context.injector)
    await web_registry.setup(context)
    registry.register(web_registry)

    legacy_indy_registry = ClassProvider(
        "aries_cloudagent.anoncreds.default.legacy_indy.registry.LegacyIndyRegistry",
        # supported_identifiers=[],
        # method_name="",
    ).provide(context.settings, context.injector)
    await legacy_indy_registry.setup(context)
    registry.register(legacy_indy_registry)

    # TODO: add context.settings
