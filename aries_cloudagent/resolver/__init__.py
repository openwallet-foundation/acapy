"""Interfaces and base classes for DID Resolution."""

from ..config.injection_context import InjectionContext
from .did_resolver_registry import DIDResolverRegistry
from .default.indy import IndyDIDResolver
from .default.http_universal import HTTPUniversalDIDResolver


async def setup(context: InjectionContext):
    """Set up default resolvers."""
    registry = context.inject(DIDResolverRegistry)
    for Resolver in (IndyDIDResolver, HTTPUniversalDIDResolver):
        resolver = Resolver()
        await resolver.setup(context)
        registry.register(resolver)
