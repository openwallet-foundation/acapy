"""Utilities for specifying which verification method is in use for a given DID."""

from abc import ABC, abstractmethod
import logging
from typing import Literal, Optional

from pydid import DIDDocument

from ..core.error import BaseError
from ..core.profile import Profile
from ..did.did_key import DIDKey
from ..resolver.did_resolver import DIDResolver

LOGGER = logging.getLogger(__name__)


ProofPurposeStr = Literal[
    "assertionMethod",
    "authentication",
    "capabilityDelegation",
    "capabilityInvocation",
]
PROOF_PURPOSES = (
    "authentication",
    "assertionMethod",
    "capabilityInvocation",
    "capabilityDelegation",
)


class VerificationKeyStrategyError(BaseError):
    """Raised on issues with verfication method derivation."""


class BaseVerificationKeyStrategy(ABC):
    """Base class for defining which verification method is in use."""

    @abstractmethod
    async def get_verification_method_id_for_did(
        self,
        did: str,
        profile: Profile,
        *,
        proof_type: Optional[str] = None,
        proof_purpose: Optional[ProofPurposeStr] = None,
    ) -> str:
        """Given a DID, returns the verification key ID in use.

        Returns None if no strategy is specified for this DID.

        :params did: the did
        :params profile: context of the call
        :params allowed_verification_method_types: list of accepted key types
        :params proof_purpose: the verkey relationship (assertionMethod, keyAgreement, ..)
        :returns Optional[str]: the current verkey ID
        """
        ...


class DefaultVerificationKeyStrategy(BaseVerificationKeyStrategy):
    """A basic implementation for verkey strategy.

    Supports did:key: and did:sov only.
    """

    def __init__(self):
        """Initialize the key types mapping."""
        self.key_types_mapping = {
            "Ed25519Signature2018": ["Ed25519VerificationKey2018"],
            "Ed25519Signature2020": ["Ed25519VerificationKey2020", "Multikey"],
        }

    async def get_verification_method_id_for_did(
        self,
        did: str,
        profile: Profile,
        *,
        proof_type: Optional[str] = None,
        proof_purpose: Optional[ProofPurposeStr] = None,
    ) -> str:
        """Given a did:key or did:sov, returns the verification key ID in use.

        Returns None if no strategy is specified for this DID.

        :params did: the did
        :params profile: context of the call
        :params allowed_verification_method_types: list of accepted key types
        :params proof_purpose: the verkey relationship (assertionMethod, keyAgreement, ..)
        :returns Optional[str]: the current verkey ID
        """
        proof_type = proof_type or "Ed25519Signature2018"
        proof_purpose = proof_purpose or "assertionMethod"

        if proof_purpose not in PROOF_PURPOSES:
            raise ValueError("Invalid proof purpose")

        if did.startswith("did:key:"):
            return DIDKey.from_did(did).key_id
        elif did.startswith("did:sov:"):
            # key-1 is what uniresolver uses for key id
            return did + "#key-1"

        resolver = profile.inject(DIDResolver)
        doc_raw = await resolver.resolve(profile=profile, did=did)
        doc = DIDDocument.deserialize(doc_raw)

        methods_or_refs = getattr(doc, proof_purpose, [])
        # Dereference any refs in the verification relationship
        methods = [
            await resolver.dereference_verification_method(profile, method, document=doc)
            if isinstance(method, str)
            else method
            for method in methods_or_refs
        ]

        method_types = self.key_types_mapping.get(proof_type)
        if not method_types:
            raise VerificationKeyStrategyError(
                f"proof type {proof_type} is not supported"
            )

        # Filter methods by type expected for proof_type
        methods = [vm for vm in methods if vm.type in method_types]
        if not methods:
            raise VerificationKeyStrategyError(
                f"No matching verification method found for did {did} with proof "
                f"type {proof_type} and purpose {proof_purpose}"
            )

        if len(methods) > 1:
            LOGGER.info(
                (
                    "More than 1 verification method matched for did %s with proof "
                    "type %s and purpose %s; returning the first: %s"
                ),
                did,
                proof_type,
                proof_purpose,
                methods[0].id,
            )

        return methods[0].id
