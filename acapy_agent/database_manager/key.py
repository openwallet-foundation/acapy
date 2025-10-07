"""Handling of Key instances."""

from typing import Any

from .db_types import KeyAlg, SeedMethod


class Key:
    """An active key or keypair instance."""

    def __init__(self, handle: Any):
        """Initialize the Key instance."""
        self._handle = handle

    @classmethod
    def generate(cls, alg: str | KeyAlg, *, ephemeral: bool = False) -> "Key":
        """Raise an error as key generation requires bindings."""
        raise NotImplementedError("Key generation is not available without bindings.")

    @classmethod
    def from_seed(
        cls,
        alg: str | KeyAlg,
        seed: str | bytes,
        *,
        method: str | SeedMethod = None,
    ) -> "Key":
        """Raise an error as seed-based key creation requires bindings."""
        raise NotImplementedError(
            "Key creation from seed is not available without bindings."
        )

    @classmethod
    def from_secret_bytes(cls, alg: str | KeyAlg, secret: bytes) -> "Key":
        """Raise an error as secret-based key creation requires bindings."""
        raise NotImplementedError(
            "Key creation from secret bytes is not available without bindings."
        )

    @classmethod
    def from_public_bytes(cls, alg: str | KeyAlg, public: bytes) -> "Key":
        """Raise an error as public-based key creation requires bindings."""
        raise NotImplementedError(
            "Key creation from public bytes is not available without bindings."
        )

    @classmethod
    def from_jwk(cls, jwk: dict | str | bytes) -> "Key":
        """Raise an error as JWK-based key creation requires bindings."""
        raise NotImplementedError(
            "Key creation from JWK is not available without bindings."
        )

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

    def convert_key(self, alg: str | KeyAlg) -> "Key":
        """Raise an error as key conversion requires bindings."""
        raise NotImplementedError("Key conversion is not available without bindings.")

    def key_exchange(self, alg: str | KeyAlg, pk: "Key") -> "Key":
        """Raise an error as key exchange requires bindings."""
        raise NotImplementedError("Key exchange is not available without bindings.")

    def get_public_bytes(self) -> bytes:
        """Return placeholder public bytes since bindings is unavailable."""
        return b"public_bytes_placeholder"

    def get_secret_bytes(self) -> bytes:
        """Return placeholder secret bytes since bindings is unavailable."""
        return b"secret_bytes_placeholder"

    def get_jwk_public(self) -> str:
        """Return placeholder public JWK since bindings is unavailable."""
        return "jwk_public_placeholder"

    def get_jwk_secret(self) -> bytes:
        """Return placeholder secret JWK since bindings is unavailable."""
        return b"jwk_secret_placeholder"

    def get_jwk_thumbprint(self) -> str:
        """Return placeholder JWK thumbprint since bindings is unavailable."""
        return "jwk_thumbprint_placeholder"

    def aead_params(self) -> str:
        """Return a placeholder for AEAD parameters."""
        return "AeadParams placeholder"

    def aead_random_nonce(self) -> bytes:
        """Return placeholder nonce since bindings is unavailable."""
        return b"nonce_placeholder"

    def aead_encrypt(
        self,
        plaintext: bytes = None,
        *,
        nonce: bytes | None = None,
        aad: bytes | None = None,
    ) -> str:
        """Return a placeholder for encrypted data."""
        return "Encrypted placeholder"

    def aead_decrypt(
        self,
        ciphertext: bytes = None,
        *,
        nonce: bytes | None = None,
        aad: bytes | None = None,
    ) -> bytes:
        """Return placeholder decrypted data."""
        return b"decrypted placeholder"

    def sign_message(self, message: str | bytes, sig_type: str = None) -> bytes:
        """Raise an error as signing requires bindings."""
        raise NotImplementedError("Message signing is not available without bindings.")

    def verify_signature(
        self, message: str | bytes, signature: bytes, sig_type: str = None
    ) -> bool:
        """Raise an error as verification requires bindings."""
        raise NotImplementedError(
            "Signature verification is not available without bindings."
        )

    def wrap_key(self, other_key=None) -> str:
        """Return a placeholder for wrapped key."""
        return "Encrypted placeholder"

    def unwrap_key(self) -> "Key":
        """Return a placeholder Key instance."""
        return Key("placeholder handle")

    def __repr__(self) -> str:
        """String representation of the Key instance."""
        return (
            f"<Key(handle={self._handle}, alg={self.algorithm}, "
            f"ephemeral={self.ephemeral})>"
        )
