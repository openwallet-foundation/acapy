"""
the did resolver.

responsible for keeping track of all resolvers. more importantly
retrieving did's from different sources provided by the method type.
"""

import logging
from typing import Union
from itertools import chain
from ..resolver.diddoc import ResolvedDIDDoc  # , ExternalResourceError
from ..resolver.base import BaseDIDResolver, DidMethodNotSupported, DidNotFound
from ..resolver.did import DID, DIDUrl  # , DID_PATTERN
from .did_resolver_registry import DIDResolverRegistry

LOGGER = logging.getLogger(__name__)


class DIDResolver:
    """did resolver singleton."""

    def __init__(self, registry: DIDResolverRegistry):
        """Initialize a `didresolver` instance."""
        self.did_resolver_registry = registry

    async def resolve(self, did: Union[str, DID]) -> ResolvedDIDDoc:
        """Retrieve did doc from public registry."""
        if isinstance(did, str):
            did = DID(did)
        for resolver in self._match_did_to_resolver(did):
            try:
                LOGGER.debug("Resolving DID %s with %s", did, resolver)
                return await resolver.resolve(did)
            except DidNotFound:
                LOGGER.debug("DID %s not found by resolver %s", did, resolver)

        raise DidNotFound(f"DID {did} could not be resolved.")

    def _match_did_to_resolver(self, did: DID) -> BaseDIDResolver:
        """Generate supported DID Resolvers.

        Native resolvers are yielded first, in registered order followed by
        non-native resolvers in registered order.
        """
        valid_resolvers = list(
            filter(
                lambda resolver: resolver.supports(did.method),
                self.did_resolver_registry.resolvers,
            )
        )
        native_resolvers = filter(lambda resolver: resolver.native, valid_resolvers)
        non_native_resolvers = filter(
            lambda resolver: not resolver.native, valid_resolvers
        )
        resolvers = list(chain(native_resolvers, non_native_resolvers))
        if not resolvers:
            raise DidMethodNotSupported(f"{did.method} not supported")
        return resolvers

    async def dereference_external(self, did_url: str) -> ResolvedDIDDoc:
        """Retrieve an external did in doc service from a public registry."""
        did_url = DIDUrl.parse(did_url)
        doc = await self.resolve(did_url.did)
        return doc.dereference(did_url)
