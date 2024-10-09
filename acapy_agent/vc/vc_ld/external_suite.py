"""Plugin hook for providing an external signature suite implementation.

This enables greater control over where JSON-LD credentials are signed without
requiring knowledge of the complexities of the JSON-LD/VC-LDP subsystem.
"""

from abc import ABC, abstractmethod
from typing import Optional

from ...core.error import BaseError
from ...core.profile import Profile
from ...wallet.did_info import DIDInfo
from ..ld_proofs.suites.linked_data_proof import LinkedDataProof


class ExternalSuiteError(BaseError):
    """Raised when an error occurs in an external signature suite provider."""


class ExternalSuiteNotFoundError(ExternalSuiteError):
    """Raised when an external signature suite provider is not found.

    This should be raised to prevent falling back to built in suites, if desired.
    """


class ExternalSuiteProvider(ABC):
    """Plugin hook for providing an external signature suite implementation."""

    @abstractmethod
    async def get_suite(
        self,
        profile: Profile,
        proof_type: str,
        proof: dict,
        verification_method: str,
        did_info: DIDInfo,
    ) -> Optional[LinkedDataProof]:
        """Get a signature suite for the given proof type and verification method.

        Implementing classes should raise ExternalSuiteNotFoundError if preventing
        fallback to built-in suites is desired. Otherwise, return None to indicate
        that the implementing class does not support the given proof type.
        """
