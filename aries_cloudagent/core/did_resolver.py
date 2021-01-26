"""
the did resolver.

responsible for keeping track of all resolvers. more importantly
retrieving did's from different sources provided by the method type.
"""

import logging
from ..resolver.diddoc import ResolvedDIDDoc, ExternalResourceError
from ..resolver.base import BaseDIDResolver
from ..resolver.did import DID
from .did_resolver_registry import DIDResolverRegistry

LOGGER = logging.getLogger(__name__)


class DIDResolver:
    """did resolver singleton."""

    def __init__(self, registry: DIDResolverRegistry):
        """Initialize a `didresolver` instance."""
        self.did_resolver_registery = registry

    async def resolve(self, did: str) -> ResolvedDIDDoc:
        # doc = self.dereference_external(did).resolve()
        return self.fully_dereference(did)

    def _match_did_to_resolver(self, did: str) -> BaseDIDResolver:
        did = DID(did)
        favored_resolver = None
        for resolver in self.did_resolver_registery:
            if resolver.supports(did.method):
                # if resolver is set only favor native, otherwise favor any
                if favored_resolver and resolver.native:
                    favored_resolver = resolver.native
                elif not favored_resolver:
                    favored_resolver = resolver
        return favored_resolver

    def dereference_external(self, did_url: str) -> ResolvedDIDDoc:
        return self._match_did_to_resolver(did_url).resolve()

    def fully_dereference(self, doc: ResolvedDIDDoc):
        for did, sub_doc in enumerate(doc._index):
            try:
                doc.dereference(did)
            except ExternalResourceError:
                try:  # FIXME: needs help
                    deref = self.dereference_external(did)
                    deep_deref = self.fully_dereference(deref)
                    doc._index[did] = deep_deref
                except Exception:
                    pass
        return doc
