"""
the did resolver.

responsible for keeping track of all resolvers. more importantly
retrieving did's from different sources provided by the method type.
"""

import logging
from typing import Union
from itertools import chain
from ..resolver.diddoc import ResolvedDIDDoc, ExternalResourceError
from ..resolver.base import BaseDIDResolver, DidMethodNotSupported, DidNotFound
from ..resolver.did import DID, DIDUrl, DID_PATTERN
from .did_resolver_registry import DIDResolverRegistry

LOGGER = logging.getLogger(__name__)


class DIDResolver:
    """did resolver singleton."""

    def __init__(self, registry: DIDResolverRegistry):
        """Initialize a `didresolver` instance."""
        self.did_resolver_registery = registry

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
        valid_resolvers = filter(
            lambda resolver: resolver.supports(did.method),
            self.did_resolver_registery.did_resolvers,
        )
        if not valid_resolvers:
            raise DidMethodNotSupported(f"{did.method} not supported")

        native_resolvers = filter(lambda resolver: resolver.native, valid_resolvers)
        non_native_resolvers = filter(
            lambda resolver: not resolver.nateive, valid_resolvers
        )
        yield from chain(native_resolvers, non_native_resolvers)

    async def dereference_external(self, did_url: str) -> ResolvedDIDDoc:
        """Retrieve an external did in doc service from a public registry."""
        did_url = DIDUrl.parse(did_url)
        doc = await self.resolve(did_url.did)
        return doc.dereference(did_url)

    async def fully_dereference(self, doc: ResolvedDIDDoc):
        """Recursivly retrieve all doc service dids from public registries."""

        async def _visit(value, doc):
            if isinstance(value, dict):
                doc_dict = {}
                for key, value in value.items():
                    doc_dict[key] = await _visit(value, doc)
                return doc
            elif isinstance(value, list):
                return [await _visit(item, doc) for item in value]
            elif isinstance(value, str):
                if DID_PATTERN.match(value):  # string is a did_url pattern
                    did_url = DIDUrl.parse(value)
                    did_str = ""
                    try:  # dereference from diddoc
                        did_str = doc.dereference(did_url)
                    except ExternalResourceError:  # dereference from a resolver
                        did_str = await self.dereference_external(did_url)
                    did_str = await _visit(did_str, doc)
                return did_str
            return value

        return await _visit(doc._doc, doc)
