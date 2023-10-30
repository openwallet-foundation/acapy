"""Base key pair class."""

from abc import ABC, abstractmethod, abstractproperty
from typing import List, Optional, Union


class KeyPair(ABC):
    """Base key pair class."""

    @abstractmethod
    async def sign(self, message: Union[List[bytes], bytes]) -> bytes:
        """Sign message(s) using key pair."""

    @abstractmethod
    async def verify(
        self, message: Union[List[bytes], bytes], signature: bytes
    ) -> bool:
        """Verify message(s) against signature using key pair."""

    @abstractproperty
    def has_public_key(self) -> bool:
        """Whether key pair has a public key.

        Public key is required for verification, but can be set dynamically
        in the verification process.
        """

    @abstractproperty
    def public_key(self) -> Optional[bytes]:
        """Getter for the public key bytes.

        Returns:
            bytes: The public key

        """

    @abstractmethod
    def from_verification_method(self, verification_method: dict) -> "KeyPair":
        """Create new key pair class based on the passed verification method."""
