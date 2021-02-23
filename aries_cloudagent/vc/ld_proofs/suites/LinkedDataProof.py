"""Abstract base class for linked data proofs."""
from abc import ABCMeta, abstractmethod

class LinkedDataProof(metaclass=ABCMeta):
  def __init__(self, signature_type: str):
    self.signature_type = signature_type

  @abstractmethod
  async def create_proof(self, options: dict):
    pass

  @abstractmethod
  async def verify_proof(self, **kwargs):
    pass

  async def match_proof(self, signature_type: str) -> bool:
    return signature_type == self.signature_type
