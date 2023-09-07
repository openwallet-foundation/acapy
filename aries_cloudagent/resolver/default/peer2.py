"""Peer DID Resolver.

Resolution is performed using the peer-did-python library https://github.com/sicpa-dlab/peer-did-python.
"""

from typing import Optional, Pattern, Sequence, Text, Union

from peerdid.dids import (
    is_peer_did,
    PEER_DID_PATTERN,
    resolve_peer_did,
    DID,
    DIDDocument,
)

from ...config.injection_context import InjectionContext
from ...core.profile import Profile
from ..base import BaseDIDResolver, DIDNotFound, ResolverType
from .peer3 import PeerDID3Resolver


class PeerDID2Resolver(BaseDIDResolver):
    """Peer DID Resolver."""

    def __init__(self):
        """Initialize Key Resolver."""
        super().__init__(ResolverType.NATIVE)

    async def setup(self, context: InjectionContext):
        """Perform required setup for Key DID resolution."""

    @property
    def supported_did_regex(self) -> Pattern:
        """Return supported_did_regex of Key DID Resolver."""
        return PEER_DID_PATTERN

    async def _resolve(
        self,
        profile: Profile,
        did: str,
        service_accept: Optional[Sequence[Text]] = None,
    ) -> dict:
        """Resolve a Key DID."""
        try:
            peer_did = is_peer_did(did)
        except Exception as e:
            raise DIDNotFound(f"peer_did is not formatted correctly: {did}") from e
        if peer_did:
            did_doc = self.resolve_peer_did_with_service_key_reference(did)
            await PeerDID3Resolver().create_and_store_document(profile, did_doc)
        else:
            raise DIDNotFound(f"did is not a peer did: {did}")

        return did_doc.dict()

    def resolve_peer_did_with_service_key_reference(
        self, peer_did_2: Union[str, DID]
    ) -> DIDDocument:
        """Generate a DIDDocument from the did:peer:2 based on peer-did-python library.

        And additional modification to ensure recipient key
        references verificationmethod in same document.
        """
        return _resolve_peer_did_with_service_key_reference(peer_did_2)


def _resolve_peer_did_with_service_key_reference(
    peer_did_2: Union[str, DID]
) -> DIDDocument:
    try:
        doc = resolve_peer_did(peer_did_2)
        ## WORKAROUND LIBRARY NOT REREFERENCING RECEIPIENT_KEY
        services = doc.service
        signing_keys = [
            vm
            for vm in doc.verification_method or []
            if vm.type == "Ed25519VerificationKey2020"
        ]
        if services and signing_keys:
            services[0].__dict__["recipient_keys"] = [signing_keys[0].id]
        else:
            raise Exception("no recipient_key signing_key pair")
    except Exception as e:
        raise ValueError("pydantic validation error:" + str(e))
    return doc
