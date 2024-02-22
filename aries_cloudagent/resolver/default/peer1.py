"""did:peer:1 resolver implementation."""

import logging
import re
from typing import Callable, Optional, Pattern, Sequence, Text, Union

from aries_cloudagent.messaging.valid import B58

from ...config.injection_context import InjectionContext
from ...connections.base_manager import BaseConnectionManager
from ...core.profile import Profile
from ...resolver.base import BaseDIDResolver, DIDNotFound, ResolverType
from ...storage.error import StorageNotFoundError


LOGGER = logging.getLogger(__name__)


# TODO Copy pasted from did-peer-4, reuse when available
def _operate_on_embedded(
    visitor: Callable[[dict], dict]
) -> Callable[[Union[dict, str]], Union[dict, str]]:
    """Return an adapter function that turns a vm visitor into a vm | ref visitor.

    The adapter function calls a visitor on embedded vms but just returns on refs.
    """

    def _adapter(vm: Union[dict, str]) -> Union[dict, str]:
        if isinstance(vm, dict):
            return visitor(vm)
        return vm

    return _adapter


def _visit_verification_methods(document: dict, visitor: Callable[[dict], dict]):
    """Visit all verification methods in a document.

    This includes the main verificationMethod list as well as verification
    methods embedded in relationships.
    """
    verification_methods = document.get("verificationMethod")
    if verification_methods:
        document["verificationMethod"] = [visitor(vm) for vm in verification_methods]

    for relationship in (
        "authentication",
        "assertionMethod",
        "keyAgreement",
        "capabilityInvocation",
        "capabilityDelegation",
    ):
        vms_and_refs = document.get(relationship)
        if vms_and_refs:
            document[relationship] = [
                _operate_on_embedded(visitor)(vm) for vm in vms_and_refs
            ]

    return document


def contextualize(did: str, document: dict):
    """Contextualize a peer DID document."""

    def _contextualize_verification_method(vm: dict):
        """Contextualize a verification method."""
        if vm["controller"] == "#id":
            vm["controller"] = did
        if vm["id"].startswith("#"):
            vm["id"] = f"{did}{vm['id']}"
        return vm

    document = _visit_verification_methods(document, _contextualize_verification_method)

    for service in document.get("service", []):
        if service["id"].startswith("#"):
            service["id"] = f"{did}{service['id']}"

    return document


class PeerDID1Resolver(BaseDIDResolver):
    """Resolve legacy peer DIDs."""

    PEER1_PATTERN = re.compile(rf"^did:peer:1zQm[{B58}]{{44}}$")

    def __init__(self):
        """Initialize the resolver instance."""
        super().__init__(ResolverType.NATIVE)

    async def setup(self, context: InjectionContext):
        """Perform required setup for the resolver."""

    @property
    def supported_did_regex(self) -> Pattern:
        """Return supported_did_regex of DID Peer 1 Resolver."""
        return self.PEER1_PATTERN

    async def _fetch_did_document(self, profile: Profile, did: str) -> Optional[dict]:
        """Fetch DID from wallet if available.

        This is the method to be used with fetch_did_document to enable caching.
        """
        conn_mgr = BaseConnectionManager(profile)
        try:
            doc, _ = await conn_mgr.fetch_did_document(did)
            LOGGER.debug("Fetched doc %s", doc)
            return doc
        except StorageNotFoundError:
            LOGGER.debug("Failed to fetch doc for did %s", did)

        return None

    async def _resolve(
        self,
        profile: Profile,
        did: str,
        service_accept: Optional[Sequence[Text]] = None,
    ) -> dict:
        """Resolve Legacy Peer DID to a DID document by fetching from the wallet.

        By the time this resolver is selected, it should be impossible for it
        to raise a DIDNotFound.
        """
        result = await self._fetch_did_document(profile, did)
        if result:
            # Apply corrections?
            result = contextualize(did, result)
            LOGGER.debug("Resolved %s to %s", did, result)
            return result
        else:
            raise DIDNotFound(f"DID not found: {did}")
