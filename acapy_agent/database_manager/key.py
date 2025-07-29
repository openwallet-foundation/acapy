"""Handling of Key instances."""

from typing import Union, Any
from .db_types import KeyAlg, SeedMethod

class Key:
    """An active key or keypair instance."""

    def __init__(self, handle: Any):
        """Initialize the Key instance."""
        self._handle = handle

    @classmethod
    def generate(cls, alg: Union[str, KeyAlg], *, ephemeral: bool = False) -> "Key":
        """Raise an error as key generation requires bindings."""
        raise NotImplementedError("Key generation is not available without bindings.")

    @classmethod
    def from_seed(
        cls,
        alg: Union[str, KeyAlg],
        seed: Union[str, bytes],
        *, 
        method: Union[str, SeedMethod] = None,
    ) -> "Key":
        """Raise an error as seed-based key creation requires bindings."""
        raise NotImplementedError("Key creation from seed is not available without bindings.")

    @classmethod
    def from_secret_bytes(cls, alg: Union[str, KeyAlg], secret: bytes) -> "Key":
        """Raise an error as secret-based key creation requires bindings."""
        raise NotImplementedError("Key creation from secret bytes is not available without bindings.")

    @classmethod
    def from_public_bytes(cls, alg: Union[str, KeyAlg], public: bytes) -> "Key":
        """Raise an error as public-based key creation requires bindings."""
        raise NotImplementedError("Key creation from public bytes is not available without bindings.")

    @classmethod
    def from_jwk(cls, jwk: Union[dict, str, bytes]) -> "Key":
        """Raise an error as JWK-based key creation requires bindings."""
        raise NotImplementedError("Key creation from JWK is not available without bindings.")

    @property
    def handle(self) -> Any:
        """Accessor for the key handle."""
        return self._handle

    @property
    def algorithm(self) -> KeyAlg:
        """Return a placeholder algorithm since bindings is unavailable."""
        return KeyAlg.A128GCM  # Placeholder value

    @property
    def ephemeral(self) -> bool:
        """Return a placeholder ephemeral flag since bindings is unavailable."""
        return False  # Placeholder value

    def convert_key(self, alg: Union[str, KeyAlg]) -> "Key":
        """Raise an error as key conversion requires bindings."""
        raise NotImplementedError("Key conversion is not available without bindings.")

    def key_exchange(self, alg: Union[str, KeyAlg], pk: "Key") -> "Key":
        """Raise an error as key exchange requires bindings."""
        raise NotImplementedError("Key exchange is not available without bindings.")

    def get_public_bytes(self) -> bytes:
        """Return placeholder public bytes since bindings is unavailable."""
        return b"public_bytes_placeholder"

    def get_secret_bytes(self) -> bytes:
        """Return placeholder secret bytes since bindings is unavailable."""
        return b"secret_bytes_placeholder"

    def get_jwk_public(self, alg: Union[str, KeyAlg] = None) -> str:
        """Return placeholder public JWK since bindings is unavailable."""
        return "jwk_public_placeholder"

    def get_jwk_secret(self) -> bytes:
        """Return placeholder secret JWK since bindings is unavailable."""
        return b"jwk_secret_placeholder"

    def get_jwk_thumbprint(self, alg: Union[str, KeyAlg] = None) -> str:
        """Return placeholder JWK thumbprint since bindings is unavailable."""
        return "jwk_thumbprint_placeholder"

    def aead_params(self) -> str:
        """Return a placeholder for AEAD parameters."""
        return "AeadParams placeholder"

    def aead_random_nonce(self) -> bytes:
        """Return placeholder nonce since bindings is unavailable."""
        return b"nonce_placeholder"

    def aead_encrypt(
        self, message: Union[str, bytes], *, nonce: bytes = None, aad: bytes = None
    ) -> str:
        """Return a placeholder for encrypted data."""
        return "Encrypted placeholder"

    def aead_decrypt(
        self,
        ciphertext: bytes,
        *,
        nonce: bytes,
        tag: bytes = None,
        aad: bytes = None,
    ) -> bytes:
        """Return placeholder decrypted data."""
        return b"decrypted placeholder"

    def sign_message(self, message: Union[str, bytes], sig_type: str = None) -> bytes:
        """Raise an error as signing requires bindings."""
        raise NotImplementedError("Message signing is not available without bindings.")

    def verify_signature(
        self, message: Union[str, bytes], signature: bytes, sig_type: str = None
    ) -> bool:
        """Raise an error as verification requires bindings."""
        raise NotImplementedError("Signature verification is not available without bindings.")

    def wrap_key(self, other: "Key", *, nonce: bytes = None) -> str:
        """Return a placeholder for wrapped key."""
        return "Encrypted placeholder"

    def unwrap_key(
        self,
        alg: Union[str, KeyAlg],
        ciphertext: bytes,
        *,
        nonce: bytes = None,
        tag: bytes = None,
    ) -> "Key":
        """Return a placeholder Key instance."""
        return Key("placeholder handle")

    def __repr__(self) -> str:
        """String representation of the Key instance."""
        return (
            f"<Key(handle={self._handle}, alg={self.algorithm}, "
            f"ephemeral={self.ephemeral})>"
        )