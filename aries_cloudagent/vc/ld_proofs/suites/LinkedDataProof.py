"""Abstract base class for linked data proofs."""

from typing import TYPE_CHECKING
from abc import ABCMeta, abstractmethod

from ..document_loader import DocumentLoader

# ProofPurpose and LinkedDataProof depend on each other
if TYPE_CHECKING:
    from ..purposes.ProofPurpose import ProofPurpose


class LinkedDataProof(metaclass=ABCMeta):
    def __init__(self, signature_type: str):
        self.signature_type = signature_type

    @abstractmethod
    async def create_proof(
        self, document: dict, purpose: "ProofPurpose", document_loader: DocumentLoader
    ) -> dict:
        pass

    @abstractmethod
    async def verify_proof(
        self,
        proof: dict,
        document: dict,
        purpose: "ProofPurpose",
        document_loader: DocumentLoader,
    ) -> dict:
        pass

    def match_proof(self, signature_type: str) -> bool:
        return signature_type == self.signature_type
