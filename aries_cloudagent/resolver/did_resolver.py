"""the did resolver.

responsible for keeping track of all resolvers. more importantly
retrieving did's from different sources provided by the method type.
"""

import asyncio
from datetime import datetime, timezone
from itertools import chain
import logging
from typing import List, Optional, Sequence, Text, Tuple, Union

from pydid import DID, DIDError, DIDUrl, Resource, VerificationMethod
import pydid
from pydid.doc.doc import BaseDIDDocument, IDNotFoundError

from ..core.profile import Profile
from .base import (
    BaseDIDResolver,
    DIDMethodNotSupported,
    DIDNotFound,
    ResolutionMetadata,
    ResolutionResult,
    ResolverError,
)

LOGGER = logging.getLogger(__name__)


class DIDResolver:
    """did resolver singleton."""

    DEFAULT_TIMEOUT = 30

    def __init__(self, resolvers: Optional[List[BaseDIDResolver]] = None):
        """Create DID Resolver."""
        self.resolvers = resolvers or []

    def register_resolver(self, resolver: BaseDIDResolver):
        """Register a new resolver."""
        self.resolvers.append(resolver)

    async def _resolve(
        self,
        profile: Profile,
        did: Union[str, DID],
        service_accept: Optional[Sequence[Text]] = None,
        *,
        timeout: Optional[int] = None,
    ) -> Tuple[BaseDIDResolver, dict]:
        """Retrieve doc and return with resolver.

        This private method enables the public resolve and resolve_with_metadata
        methods to share the same logic.
        """
        if isinstance(did, DID):
            did = str(did)
        else:
            DID.validate(did)
        for resolver in await self._match_did_to_resolver(profile, did):
            try:
                LOGGER.debug("Resolving DID %s with %s", did, resolver)
                document = await asyncio.wait_for(
                    resolver.resolve(
                        profile,
                        did,
                        service_accept,
                    ),
                    timeout if timeout is not None else self.DEFAULT_TIMEOUT,
                )
                LOGGER.debug("Resolved DID %s with %s: %s", did, resolver, document)
                return resolver, document
            except DIDNotFound:
                LOGGER.debug("DID %s not found by resolver %s", did, resolver)

        raise DIDNotFound(f"DID {did} could not be resolved")

    async def resolve(
        self,
        profile: Profile,
        did: Union[str, DID],
        service_accept: Optional[Sequence[Text]] = None,
        *,
        timeout: Optional[int] = None,
    ) -> dict:
        """Resolve a DID."""
        _, doc = await self._resolve(profile, did, service_accept, timeout=timeout)
        return doc

    async def resolve_with_metadata(
        self, profile: Profile, did: Union[str, DID], *, timeout: Optional[int] = None
    ) -> ResolutionResult:
        """Resolve a DID and return the ResolutionResult."""
        resolution_start_time = datetime.now(tz=timezone.utc)

        resolver, doc = await self._resolve(profile, did, timeout=timeout)

        time_now = datetime.now(tz=timezone.utc)
        duration = int((time_now - resolution_start_time).total_seconds() * 1000)
        retrieved_time = time_now.strftime("%Y-%m-%dT%H:%M:%SZ")
        resolver_metadata = ResolutionMetadata(
            resolver.type, type(resolver).__qualname__, retrieved_time, duration
        )
        return ResolutionResult(doc, resolver_metadata)

    async def _match_did_to_resolver(
        self, profile: Profile, did: str
    ) -> Sequence[BaseDIDResolver]:
        """Generate supported DID Resolvers.

        Native resolvers are yielded first, in registered order followed by
        non-native resolvers in registered order.
        """
        valid_resolvers = [
            resolver
            for resolver in self.resolvers
            if await resolver.supports(profile, did)
        ]
        LOGGER.debug("Valid resolvers for DID %s: %s", did, valid_resolvers)
        native_resolvers = filter(lambda resolver: resolver.native, valid_resolvers)
        non_native_resolvers = filter(
            lambda resolver: not resolver.native, valid_resolvers
        )
        resolvers = list(chain(native_resolvers, non_native_resolvers))
        if not resolvers:
            raise DIDMethodNotSupported(f'No resolver supporting DID "{did}" loaded')
        return resolvers

    async def dereference(
        self,
        profile: Profile,
        did_url: str,
        *,
        document: Optional[BaseDIDDocument] = None,
    ) -> Resource:
        """Dereference a DID URL to its corresponding DID Doc object."""
        try:
            parsed = DIDUrl.parse(did_url)
            if not parsed.did and not document:
                raise ValueError("Invalid DID URL")
        except DIDError as err:
            raise ResolverError(
                "Failed to parse DID URL from {}".format(did_url)
            ) from err

        if document and parsed.did and parsed.did != document.id:
            document = None

        if not document:
            doc_dict = await self.resolve(profile, parsed.did)
            document = pydid.deserialize_document(doc_dict)

        try:
            return document.dereference(parsed)
        except IDNotFoundError as error:
            raise ResolverError(
                "Failed to dereference DID URL: {}".format(error)
            ) from error

    async def dereference_verification_method(
        self,
        profile: Profile,
        did_url: str,
        *,
        document: Optional[BaseDIDDocument] = None,
    ) -> VerificationMethod:
        """Dereference a DID URL to a verification method."""
        dereferenced = await self.dereference(profile, did_url, document=document)
        if isinstance(dereferenced, VerificationMethod):
            return dereferenced
        raise ValueError("DID URL does not dereference to a verification method")
