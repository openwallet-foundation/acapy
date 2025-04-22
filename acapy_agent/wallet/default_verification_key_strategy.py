"""Utilities for specifying which verification method is in use for a given DID."""

import logging
from abc import ABC, abstractmethod
from typing import Literal, Optional

from pydid import DIDDocument, VerificationMethod

from acapy_agent.wallet.key_type import BLS12381G2, ED25519, P256
from acapy_agent.wallet.keys.manager import (
    MultikeyManager,
    key_type_from_multikey,
    multikey_from_verification_method,
)

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
        verification_method_id: Optional[str] = None,
    ) -> str:
        """Find suitable VerificationMethod.

        Given a DID and other verification method requirements,
        find and return the first suitable verification method ID.
        Throws if no suitable verification method

        :params did: the did
        :params profile: context of the call
        :params proof_type: the JSON-LD proof type which the verification method
            should be able to produce.
        :params proof_purpose: the verkey relationship (assertionMethod, keyAgreement, ..)
        :params verification_method_id: the verification method ID which must match.
        :returns str: the first suitable verification method
        """
        ...


class DefaultVerificationKeyStrategy(BaseVerificationKeyStrategy):
    """A basic implementation for verkey strategy."""

    def __init__(self):
        """Initialize the key types mapping.

        Map of LDP signature suite (proofType) to suitable key types
        """
        self.key_types_mapping = {
            "Ed25519Signature2018": [ED25519],
            "Ed25519Signature2020": [ED25519],
            "EcdsaSecp256r1Signature2019": [P256],
            "BbsBlsSignature2020": [BLS12381G2],
            "BbsBlsSignatureProof2020": [BLS12381G2],
        }

    async def get_verification_method_id_for_did(
        self,
        did: str,
        profile: Profile,
        *,
        proof_type: Optional[str] = None,
        proof_purpose: Optional[ProofPurposeStr] = None,
        verification_method_id: Optional[str] = None,
    ) -> str:
        """Find suitable VerificationMethod."""
        proof_type = proof_type or "Ed25519Signature2018"
        proof_purpose = proof_purpose or "assertionMethod"

        if proof_purpose not in PROOF_PURPOSES:
            raise ValueError("Invalid proof purpose")

        # handle default hardcoded cases
        if did.startswith("did:key:"):
            return DIDKey.from_did(did).key_id
        elif did.startswith("did:sov:"):
            # key-1 is what uniresolver uses for key id
            return did + "#key-1"

        suitable_key_types = self.key_types_mapping.get(proof_type)
        if not suitable_key_types:
            raise VerificationKeyStrategyError(
                f"proof type {proof_type} is not supported"
            )

        # TODO - if the local representation of the DID contains all this information,
        #   DID resolution cost could be avoided. However, for now there is not adequate
        #   information locally to determine if a DID/VM is suitable.

        # else, handle generically for any DID
        resolver = profile.inject(DIDResolver)
        doc_raw = await resolver.resolve(profile=profile, did=did)
        doc = DIDDocument.deserialize(doc_raw)

        # get verification methods for the proof purpose
        methods_or_refs = doc_raw.get(proof_purpose, [])

        # apply various filters to determine set of suitable verification methods
        suitable_methods = []
        async with profile.session() as session:
            key_manager = MultikeyManager(session=session)
            for method_or_ref in methods_or_refs:
                # Dereference any refs in the verification relationship
                if isinstance(method_or_ref, str):
                    method = await resolver.dereference_verification_method(
                        profile, method_or_ref, document=doc
                    )
                else:
                    method = VerificationMethod.deserialize(method_or_ref)

                    # filter for a specific verification method ID if one was specified
                if verification_method_id is not None:
                    if method.id != verification_method_id:
                        continue

                vm_multikey = multikey_from_verification_method(method)

                # filter methods by key type expected for proof_type
                vm_key_type = key_type_from_multikey(vm_multikey)
                if vm_key_type not in suitable_key_types:
                    continue

                # filter methods for keys actually owned by the wallet
                if not await key_manager.multikey_exists(
                    multikey_from_verification_method(method)
                ):
                    continue

                # survived all filters
                suitable_methods.append(method)

        if not suitable_methods:
            raise VerificationKeyStrategyError(
                f"No matching verification method found for did {did} with proof "
                f"type {proof_type} and purpose {proof_purpose}"
            )

        if len(suitable_methods) > 1:
            LOGGER.info(
                (
                    "More than 1 verification method matched for did %s with proof "
                    "type %s and purpose %s; returning the first: %s"
                ),
                did,
                proof_type,
                proof_purpose,
                suitable_methods[0].id,
            )

        return suitable_methods[0].id
