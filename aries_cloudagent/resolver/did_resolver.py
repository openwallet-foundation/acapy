"""
the did resolver.

responsible for keeping track of all resolvers. more importantly
retrieving did's from different sources provided by the method type.
"""

import logging
from itertools import chain
from datetime import datetime
from typing import Sequence, Tuple, Union

from pydid import DID, DIDError, DIDUrl, Service, VerificationMethod, DIDDocument

from ..core.profile import Profile

from .base import (
    BaseDIDResolver,
    DIDMethodNotSupported,
    DIDNotFound,
    ResolverError,
    ResolutionResult,
    ResolutionMetadata,
)
from .did_resolver_registry import DIDResolverRegistry

LOGGER = logging.getLogger(__name__)


class DIDResolver:
    """did resolver singleton."""

    def __init__(self, registry: DIDResolverRegistry):
        """Create DID Resolver."""
        self.did_resolver_registry = registry

    async def _resolve(
        self, profile: Profile, did: Union[str, DID]
    ) -> Tuple[BaseDIDResolver, DIDDocument]:
        """Retrieve doc and return with resolver."""
        # TODO Cache results
        py_did = DID(did) if isinstance(did, str) else did
        for resolver in self._match_did_to_resolver(py_did):
            try:
                LOGGER.debug("Resolving DID %s with %s", did, resolver)
                document = await resolver.resolve(
                    profile,
                    py_did,
                )
                return resolver, document
            except DIDNotFound:
                LOGGER.debug("DID %s not found by resolver %s", did, resolver)

        raise DIDNotFound(f"DID {did} could not be resolved")

    async def resolve(self, profile: Profile, did: Union[str, DID]) -> DIDDocument:
        """Resolve a DID."""
        _, doc = await self._resolve(profile, did)
        return doc

    async def resolve_with_metadata(
        self, profile: Profile, did: Union[str, DID]
    ) -> ResolutionResult:
        """Resolve a DID and return the ResolutionResult."""
        resolution_start_time = datetime.utcnow()

        resolver, doc = await self._resolve(profile, did)

        time_now = datetime.utcnow()
        duration = int((time_now - resolution_start_time).total_seconds() * 1000)
        retrieved_time = time_now.strftime("%Y-%m-%dT%H:%M:%SZ")
        resolver_metadata = ResolutionMetadata(
            resolver.type, type(resolver).__qualname__, retrieved_time, duration
        )
        return ResolutionResult(doc, resolver_metadata)

    def _match_did_to_resolver(self, py_did: DID) -> Sequence[BaseDIDResolver]:
        """Generate supported DID Resolvers.

        Native resolvers are yielded first, in registered order followed by
        non-native resolvers in registered order.
        """
        valid_resolvers = list(
            filter(
                lambda resolver: resolver.supports(py_did.method),
                self.did_resolver_registry.resolvers,
            )
        )
        native_resolvers = filter(lambda resolver: resolver.native, valid_resolvers)
        non_native_resolvers = filter(
            lambda resolver: not resolver.native, valid_resolvers
        )
        resolvers = list(chain(native_resolvers, non_native_resolvers))
        if not resolvers:
            raise DIDMethodNotSupported(f"DID method '{py_did.method}' not supported")
        return resolvers

    async def dereference(
        self, profile: Profile, did_url: str
    ) -> Union[Service, VerificationMethod]:
        """Dereference a DID URL to its corresponding DID Doc object."""
        # TODO Use cached DID Docs when possible
        try:
            did_url = DIDUrl.parse(did_url)
            document = await self.resolve(profile, did_url.did)
            return document.dereference(did_url)
        except DIDError as err:
            raise ResolverError(
                "Failed to parse DID URL from {}".format(did_url)
            ) from err
