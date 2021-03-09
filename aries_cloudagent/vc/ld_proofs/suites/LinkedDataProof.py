"""Abstract base class for linked data proofs."""
from ..purposes.ProofPurpose import ProofPurpose
from ..document_loader import DocumentLoader

from abc import ABCMeta, abstractmethod


class LinkedDataProof(metaclass=ABCMeta):
    def __init__(self, signature_type: str):
        self.signature_type = signature_type

    @abstractmethod
    async def create_proof(
        self, *, document: dict, purpose: ProofPurpose, document_loader: DocumentLoader
    ):
        pass

    @abstractmethod
    async def verify_proof(self, **kwargs):
        """TODO update method signature"""
        pass

    async def match_proof(self, signature_type: str) -> bool:
        return signature_type == self.signature_type


__all__ = [LinkedDataProof]
