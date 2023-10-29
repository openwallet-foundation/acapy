"""Interfaces and base classes for DID Resolution."""

import logging

from ..config.injection_context import InjectionContext
from ..config.provider import ClassProvider

from ..resolver.did_resolver import DIDResolver

LOGGER = logging.getLogger(__name__)


async def setup(context: InjectionContext):
    """Set up default resolvers."""
    registry = context.inject_or(DIDResolver)
    if not registry:
        LOGGER.warning("No DID Resolver instance found in context")
        return

    legacy_resolver = ClassProvider(
        "aries_cloudagent.resolver.default.legacy_peer.LegacyPeerDIDResolver"
    ).provide(context.settings, context.injector)
    await legacy_resolver.setup(context)
    registry.register_resolver(legacy_resolver)

    key_resolver = ClassProvider(
        "aries_cloudagent.resolver.default.key.KeyDIDResolver"
    ).provide(context.settings, context.injector)
    await key_resolver.setup(context)
    registry.register_resolver(key_resolver)

    if not context.settings.get("ledger.disabled"):
        indy_resolver = ClassProvider(
            "aries_cloudagent.resolver.default.indy.IndyDIDResolver"
        ).provide(context.settings, context.injector)
        await indy_resolver.setup(context)
        registry.register_resolver(indy_resolver)
    else:
        LOGGER.warning("Ledger is not configured, not loading IndyDIDResolver")

    web_resolver = ClassProvider(
        "aries_cloudagent.resolver.default.web.WebDIDResolver"
    ).provide(context.settings, context.injector)
    await web_resolver.setup(context)
    registry.register_resolver(web_resolver)

    if context.settings.get("resolver.universal"):
        universal_resolver = ClassProvider(
            "aries_cloudagent.resolver.default.universal.UniversalResolver"
        ).provide(context.settings, context.injector)
        await universal_resolver.setup(context)
        registry.register_resolver(universal_resolver)
