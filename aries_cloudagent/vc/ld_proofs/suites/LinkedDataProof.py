"""Abstract base class for linked data proofs."""

from typing import TYPE_CHECKING
from abc import ABCMeta, abstractmethod

from ..document_loader import DocumentLoader
from ..validation_result import ProofResult

# ProofPurpose and LinkedDataProof depend on each other
if TYPE_CHECKING:
    from ..purposes.ProofPurpose import ProofPurpose


class LinkedDataProof(metaclass=ABCMeta):
    """Base Linked data proof"""

    def __init__(self, *, signature_type: str, proof: dict = None):
        """Initialize new LinkedDataProof instance"""
        self.signature_type = signature_type
        self.proof = proof

    @abstractmethod
    async def create_proof(
        self,
        *,
        document: dict,
        purpose: "ProofPurpose",
        document_loader: DocumentLoader,
    ) -> dict:
        """Create proof for document

        Args:
            document (dict): The document to create the proof for
            purpose (ProofPurpose): The proof purpose to include in the proof
            document_loader (DocumentLoader): Document loader used for resolving

        Returns:
            dict: The proof object
        """

    @abstractmethod
    async def verify_proof(
        self,
        *,
        proof: dict,
        document: dict,
        purpose: "ProofPurpose",
        document_loader: DocumentLoader,
    ) -> ProofResult:
        """Verify proof against document and proof purpose.

        Args:
            proof (dict): The proof to verify
            document (dict): The document to verify the proof against
            purpose (ProofPurpose): The proof purpose to verify the proof against
            document_loader (DocumentLoader): Document loader used for resolving

        Returns:
            ValidationResult: The results of the proof verification
        """

    def match_proof(self, signature_type: str) -> bool:
        """Match signature type to signature type of this suite"""
        return signature_type == self.signature_type
