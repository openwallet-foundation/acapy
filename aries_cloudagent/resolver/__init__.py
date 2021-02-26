"""Interfaces and base classes for DID Resolution."""

import logging

from ..config.injection_context import InjectionContext
from .default.indy import IndyDIDResolver
from .did_resolver_registry import DIDResolverRegistry

LOGGER = logging.getLogger(__name__)


async def setup(context: InjectionContext):
    """Set up default resolvers."""
    registry = context.inject(DIDResolverRegistry, required=False)
    if not registry:
        LOGGER.warning("No DID Resolver Registry instance found in context")
        return

    resolver = IndyDIDResolver()
    await resolver.setup(context)
    registry.register(resolver)
