"""Utilities for specifying which verification method is in use for a given DID."""

from abc import ABC, abstractmethod
from typing import List, Optional

from acapy_agent.core.profile import Profile
from acapy_agent.did.did_key import DIDKey
from acapy_agent.wallet.key_type import KeyType

from acapy_agent.resolver.did_resolver import DIDResolver


class BaseVerificationKeyStrategy(ABC):
    """Base class for defining which verification method is in use."""

    @abstractmethod
    async def get_verification_method_id_for_did(
        self,
        did: str,
        profile: Optional[Profile],
        proof_type: Optional[str] = None,
        allowed_verification_method_types: Optional[List[KeyType]] = None,
        proof_purpose: Optional[str] = None,
    ) -> Optional[str]:
        """Given a DID, returns the verification key ID in use.

        Returns None if no strategy is specified for this DID.

        :params did: the did
        :params profile: context of the call
        :params allowed_verification_method_types: list of accepted key types
        :params proof_purpose: the verkey relationship (assertionMethod, keyAgreement, ..)
        :returns Optional[str]: the current verkey ID
        """
        pass


class DefaultVerificationKeyStrategy(BaseVerificationKeyStrategy):
    """A basic implementation for verkey strategy.

    Supports did:key: and did:sov only.
    """
    def __init__(self):
        """Initialize the key types mapping."""
        self.key_types_mapping = {
            "Ed25519Signature2018": "Ed25519VerificationKey2018",
            "Ed25519Signature2020": "Ed25519VerificationKey2020",
        }

    async def get_verification_method_id_for_did(
        self,
        did: str,
        profile: Optional[Profile],
        proof_type: Optional[str] = None,
        allowed_verification_method_types: Optional[List[KeyType]] = None,
        proof_purpose: Optional[str] = None,
    ) -> Optional[str]:
        """Given a did:key or did:sov, returns the verification key ID in use.

        Returns None if no strategy is specified for this DID.

        :params did: the did
        :params profile: context of the call
        :params allowed_verification_method_types: list of accepted key types
        :params proof_purpose: the verkey relationship (assertionMethod, keyAgreement, ..)
        :returns Optional[str]: the current verkey ID
        """
        if did.startswith("did:key:"):
            return DIDKey.from_did(did).key_id
        elif did.startswith("did:sov:"):
            # key-1 is what uniresolver uses for key id
            return did + "#key-1"
        elif did.startswith("did:web:"):
            did_resolver = profile.inject(DIDResolver)
            did_document = await did_resolver.resolve(profile=profile, did=did)
            if proof_type:
                verification_method_type = self.key_types_mapping[proof_type]
                verification_method_list = did_document.get("verificationMethod", None)
                for method in verification_method_list:
                    if method.get("type") == verification_method_type:
                        return method.get("id")
            else:
                # taking the first verification method from did document
                verification_method_id = verification_method_list[0].get("id")
                return verification_method_id
        return None
