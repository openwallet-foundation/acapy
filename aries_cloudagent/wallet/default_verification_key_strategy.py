"""Utilities for specifying which verification method is in use for a given DID."""
from abc import ABC, abstractmethod
from typing import Optional

from aries_cloudagent.did.did_key import DIDKey


class DefaultVerificationKeyStrategyBase(ABC):
    """Base class for defining which verification method is in use."""

    @abstractmethod
    def get_verification_method_id_for_did(self, did) -> Optional[str]:
        """Given a DID, returns the verification key ID in use.

        Returns None if no strategy is specified for this DID.

        :params str did: the did
        :returns Optional[str]: the current verkey ID
        """
        pass


class DefaultVerificationKeyStrategy(DefaultVerificationKeyStrategyBase):
    """A basic implementation for verkey strategy.

    Supports did:key: and did:sov only.
    """

    def get_verification_method_id_for_did(self, did) -> Optional[str]:
        """Given a did:key or did:sov, returns the verification key ID in use.

        Returns None if no strategy is specified for this DID.

        :params str did: the did
        :returns Optional[str]: the current verkey ID
        """
        if did.startswith("did:key:"):
            return DIDKey.from_did(did).key_id
        elif did.startswith("did:sov:"):
            # key-1 is what uniresolver uses for key id
            return did + "#key-1"

        return None
