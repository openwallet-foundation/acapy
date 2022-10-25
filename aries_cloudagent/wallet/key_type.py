"""Key type code."""

from typing import Optional


class KeyType:
    """Key Type class."""

    def __init__(self, key_type: str, multicodec_name: str, multicodec_prefix: bytes):
        """Construct key type."""
        self._type: str = key_type
        self._name: str = multicodec_name
        self._prefix: bytes = multicodec_prefix

    @property
    def key_type(self) -> str:
        """Get Key type, type."""
        return self._type

    @property
    def multicodec_name(self) -> str:
        """Get key type multicodec name."""
        return self._name

    @property
    def multicodec_prefix(self) -> bytes:
        """Get key type multicodec prefix."""
        return self._prefix


# NOTE: the py_multicodec library is outdated. We use hardcoded prefixes here
# until this PR gets released: https://github.com/multiformats/py-multicodec/pull/14
# multicodec is also not used now, but may be used again if py_multicodec is updated
ED25519: KeyType = KeyType("ed25519", "ed25519-pub", b"\xed\x01")
X25519: KeyType = KeyType("x25519", "x25519-pub", b"\xec\x01")
BLS12381G1: KeyType = KeyType("bls12381g1", "bls12_381-g1-pub", b"\xea\x01")
BLS12381G2: KeyType = KeyType("bls12381g2", "bls12_381-g2-pub", b"\xeb\x01")
BLS12381G1G2: KeyType = KeyType("bls12381g1g2", "bls12_381-g1g2-pub", b"\xee\x01")


class KeyTypes:
    """KeyType class specifying key types with multicodec name."""

    def __init__(self) -> None:
        """Construct key type registry."""
        self._type_registry: dict[str, KeyType] = {
            ED25519.key_type: ED25519,
            X25519.key_type: X25519,
            BLS12381G1.key_type: BLS12381G1,
            BLS12381G2.key_type: BLS12381G2,
            BLS12381G1G2.key_type: BLS12381G1G2,
        }
        self._name_registry: dict[str, KeyType] = {
            ED25519.multicodec_name: ED25519,
            X25519.multicodec_name: X25519,
            BLS12381G1.multicodec_name: BLS12381G1,
            BLS12381G2.multicodec_name: BLS12381G2,
            BLS12381G1G2.multicodec_name: BLS12381G1G2,
        }
        self._prefix_registry: dict[bytes, KeyType] = {
            ED25519.multicodec_prefix: ED25519,
            X25519.multicodec_prefix: X25519,
            BLS12381G1.multicodec_prefix: BLS12381G1,
            BLS12381G2.multicodec_prefix: BLS12381G2,
            BLS12381G1G2.multicodec_prefix: BLS12381G1G2,
        }

    def register(self, key_type: KeyType):
        """Register a new key type."""
        self._type_registry[key_type.key_type] = key_type
        self._name_registry[key_type.multicodec_name] = key_type
        self._prefix_registry[key_type.multicodec_prefix] = key_type

    def from_multicodec_name(self, multicodec_name: str) -> Optional["KeyType"]:
        """Get KeyType instance based on multicodec name. Returns None if not found."""
        return self._name_registry.get(multicodec_name)

    def from_multicodec_prefix(self, multicodec_prefix: bytes) -> Optional["KeyType"]:
        """Get KeyType instance based on multicodec prefix. Returns None if not found."""
        return self._prefix_registry.get(multicodec_prefix)

    def from_prefixed_bytes(self, prefixed_bytes: bytes) -> Optional["KeyType"]:
        """Get KeyType instance based on prefix in bytes. Returns None if not found."""
        return next(
            (
                key_type
                for key_type in self._name_registry.values()
                if prefixed_bytes.startswith(key_type.multicodec_prefix)
            ),
            None,
        )

    def from_key_type(self, key_type: str) -> Optional["KeyType"]:
        """Get KeyType instance from the key type identifier."""
        return self._type_registry.get(key_type)
