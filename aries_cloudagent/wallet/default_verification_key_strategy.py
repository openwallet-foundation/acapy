"""Utilities for specifying which verification method is in use for a given DID."""
from abc import ABC, abstractmethod
from typing import Optional, List

from aries_cloudagent.core.profile import Profile

from aries_cloudagent.wallet.key_type import KeyType
from aries_cloudagent.wallet.base import BaseWallet, DIDInfo

from aries_cloudagent.did.did_key import DIDKey


class BaseVerificationKeyStrategy(ABC):
    """Base class for defining which verification method is in use."""

    @abstractmethod
    async def get_verification_method_id_for_did(
        self,
        did: str,
        profile: Optional[Profile],
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

    @abstractmethod
    async def get_verification_key_for_did(
        self,
        did: str,
        profile: Profile,
        verification_method: Optional[str] = None,
    ) -> DIDInfo:
        """Given a DID, returns the associated DIDInfo from the wallet.

        :params did: the did
        :params profile: context of the call
        :params verification_method: verification method ID for convenience
        :returns DIDInfo: DIDInfo for the give did
        """
        pass


class DefaultVerificationKeyStrategy(BaseVerificationKeyStrategy):
    """A basic implementation for verkey strategy.

    Supports did:key: and did:sov only.
    """

    async def get_verification_method_id_for_did(
        self,
        did: str,
        profile: Optional[Profile],
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

        return None

    async def get_verification_key_for_did(
        self,
        did: str,
        profile: Profile,
        verification_method: Optional[str] = None,
    ) -> DIDInfo:
        """Given a DID, returns the associated DIDInfo from the wallet.

        :params did: the did
        :params profile: context of the call
        :params verification_method: verification method ID for convenience
        :returns DIDInfo: DIDInfo for the give did
        """
        async with profile.session() as session:
            wallet = session.inject(BaseWallet)
            did = did.replace("did:sov:", "") if did.startswith("did:sov:") else did

            return await wallet.get_local_did(did)
