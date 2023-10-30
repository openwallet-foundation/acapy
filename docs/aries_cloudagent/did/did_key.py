"""DID Key class and resolver methods."""

from ..wallet.crypto import ed25519_pk_to_curve25519
from ..wallet.key_type import (
    BLS12381G1G2,
    ED25519,
    KeyType,
    BLS12381G1,
    X25519,
    BLS12381G2,
    KeyTypes,
)
from ..wallet.util import b58_to_bytes, bytes_to_b58

from ..vc.ld_proofs.constants import DID_V1_CONTEXT_URL


class DIDKey:
    """DID Key parser and resolver."""

    _key_type: KeyType
    _public_key: bytes

    def __init__(self, public_key: bytes, key_type: KeyType) -> None:
        """Initialize new DIDKey instance."""
        self._public_key = public_key
        self._key_type = key_type

    @classmethod
    def from_public_key(cls, public_key: bytes, key_type: KeyType) -> "DIDKey":
        """Initialize new DIDKey instance from public key and key type."""

        return cls(public_key, key_type)

    @classmethod
    def from_public_key_b58(cls, public_key: str, key_type: KeyType) -> "DIDKey":
        """Initialize new DIDKey instance from base58 encoded public key and key type."""
        public_key_bytes = b58_to_bytes(public_key)
        return cls.from_public_key(public_key_bytes, key_type)

    @classmethod
    def from_fingerprint(cls, fingerprint: str, key_types=None) -> "DIDKey":
        """Initialize new DIDKey instance from multibase encoded fingerprint.

        The fingerprint contains both the public key and key type.
        """
        # Assert fingerprint is in multibase format
        assert fingerprint[0] == "z"

        # Get key bytes, remove multicodec prefix
        key_bytes_with_prefix = b58_to_bytes(fingerprint[1:])

        # Get associated key type with prefixed bytes
        if not key_types:
            key_types = KeyTypes()
        key_type = key_types.from_prefixed_bytes(key_bytes_with_prefix)

        if not key_type:
            raise Exception(
                f"No key type for prefixed public key '{key_bytes_with_prefix}' found."
            )

        # Remove the prefix bytes to get the public key
        prefix_len = len(key_type.multicodec_prefix)
        public_key_bytes = key_bytes_with_prefix[prefix_len:]

        return cls(public_key_bytes, key_type)

    @classmethod
    def from_did(cls, did: str) -> "DIDKey":
        """Initialize a new DIDKey instance from a fully qualified did:key string.

        Extracts the fingerprint from the did:key and uses that to constrcut the did:key.
        """
        did_parts = did.split("#")
        _, fingerprint = did_parts[0].split("did:key:")

        return cls.from_fingerprint(fingerprint)

    @property
    def prefixed_public_key(self) -> bytes:
        """Getter for multicodec prefixed public key."""
        return b"".join([self.key_type.multicodec_prefix, self.public_key])

    @property
    def fingerprint(self) -> str:
        """Getter for did key fingerprint."""
        return f"z{bytes_to_b58(self.prefixed_public_key)}"

    @property
    def did(self) -> str:
        """Getter for full did:key string."""
        return f"did:key:{self.fingerprint}"

    @property
    def did_doc(self) -> dict:
        """Getter for did document associated with did:key."""
        resolver = DID_KEY_RESOLVERS[self.key_type]
        return resolver(self)

    @property
    def public_key(self) -> bytes:
        """Getter for public key."""
        return self._public_key

    @property
    def public_key_b58(self) -> str:
        """Getter for base58 encoded public key."""
        return bytes_to_b58(self.public_key)

    @property
    def key_type(self) -> KeyType:
        """Getter for key type."""
        return self._key_type

    @property
    def key_id(self) -> str:
        """Getter for key id."""
        return f"{self.did}#{self.fingerprint}"


def construct_did_key_bls12381g2(did_key: "DIDKey") -> dict:
    """Construct BLS12381G2 did:key.

    Args:
        did_key (DIDKey): did key instance to parse bls12381g2 did:key document from

    Returns:
        dict: The bls12381g2 did:key did document

    """

    return construct_did_signature_key_base(
        id=did_key.did,
        key_id=did_key.key_id,
        verification_method={
            "id": did_key.key_id,
            "type": "Bls12381G2Key2020",
            "controller": did_key.did,
            "publicKeyBase58": did_key.public_key_b58,
        },
    )


def construct_did_key_bls12381g1(did_key: "DIDKey") -> dict:
    """Construct BLS12381G1 did:key.

    Args:
        did_key (DIDKey): did key instance to parse bls12381g1 did:key document from

    Returns:
        dict: The bls12381g1 did:key did document

    """

    return construct_did_signature_key_base(
        id=did_key.did,
        key_id=did_key.key_id,
        verification_method={
            "id": did_key.key_id,
            "type": "Bls12381G1Key2020",
            "controller": did_key.did,
            "publicKeyBase58": did_key.public_key_b58,
        },
    )


def construct_did_key_bls12381g1g2(did_key: "DIDKey") -> dict:
    """Construct BLS12381G1G2 did:key.

    Args:
        did_key (DIDKey): did key instance to parse bls12381g1g2 did:key document from

    Returns:
        dict: The bls12381g1g2 did:key did document

    """

    g1_public_key = did_key.public_key[:48]
    g2_public_key = did_key.public_key[48:]

    bls12381g1_key = DIDKey.from_public_key(g1_public_key, BLS12381G1)
    bls12381g2_key = DIDKey.from_public_key(g2_public_key, BLS12381G2)

    bls12381g1_key_id = f"{did_key.did}#{bls12381g1_key.fingerprint}"
    bls12381g2_key_id = f"{did_key.did}#{bls12381g2_key.fingerprint}"

    return {
        "@context": DID_V1_CONTEXT_URL,
        "id": did_key.did,
        "verificationMethod": [
            {
                "id": bls12381g1_key_id,
                "type": "Bls12381G1Key2020",
                "controller": did_key.did,
                "publicKeyBase58": bls12381g1_key.public_key_b58,
            },
            {
                "id": bls12381g2_key_id,
                "type": "Bls12381G2Key2020",
                "controller": did_key.did,
                "publicKeyBase58": bls12381g2_key.public_key_b58,
            },
        ],
        "authentication": [bls12381g1_key_id, bls12381g2_key_id],
        "assertionMethod": [bls12381g1_key_id, bls12381g2_key_id],
        "capabilityDelegation": [bls12381g1_key_id, bls12381g2_key_id],
        "capabilityInvocation": [bls12381g1_key_id, bls12381g2_key_id],
        "keyAgreement": [],
    }


def construct_did_key_x25519(did_key: "DIDKey") -> dict:
    """Construct X25519 did:key.

    Args:
        did_key (DIDKey): did key instance to parse x25519 did:key document from

    Returns:
        dict: The x25519 did:key did document

    """

    return {
        "@context": DID_V1_CONTEXT_URL,
        "id": did_key.did,
        "verificationMethod": [
            {
                "id": did_key.key_id,
                "type": "X25519KeyAgreementKey2019",
                "controller": did_key.did,
                "publicKeyBase58": did_key.public_key_b58,
            },
        ],
        "authentication": [],
        "assertionMethod": [],
        "capabilityDelegation": [],
        "capabilityInvocation": [],
        "keyAgreement": [did_key.key_id],
    }


def construct_did_key_ed25519(did_key: "DIDKey") -> dict:
    """Construct Ed25519 did:key.

    Args:
        did_key (DIDKey): did key instance to parse ed25519 did:key document from

    Returns:
        dict: The ed25519 did:key did document

    """
    curve25519 = ed25519_pk_to_curve25519(did_key.public_key)
    x25519 = DIDKey.from_public_key(curve25519, X25519)

    did_doc = construct_did_signature_key_base(
        id=did_key.did,
        key_id=did_key.key_id,
        verification_method={
            "id": did_key.key_id,
            "type": "Ed25519VerificationKey2018",
            "controller": did_key.did,
            "publicKeyBase58": did_key.public_key_b58,
        },
    )

    # Ed25519 has pair with X25519
    did_doc["keyAgreement"].append(
        {
            "id": f"{did_key.did}#{x25519.fingerprint}",
            "type": "X25519KeyAgreementKey2019",
            "controller": did_key.did,
            "publicKeyBase58": bytes_to_b58(curve25519),
        }
    )

    return did_doc


def construct_did_signature_key_base(
    *, id: str, key_id: str, verification_method: dict
):
    """Create base did key structure to use for most signature keys.

    May not be suitable for all did key types

    """

    return {
        "@context": DID_V1_CONTEXT_URL,
        "id": id,
        "verificationMethod": [verification_method],
        "authentication": [key_id],
        "assertionMethod": [key_id],
        "capabilityDelegation": [key_id],
        "capabilityInvocation": [key_id],
        "keyAgreement": [],
    }


DID_KEY_RESOLVERS = {
    ED25519: construct_did_key_ed25519,
    X25519: construct_did_key_x25519,
    BLS12381G2: construct_did_key_bls12381g2,
    BLS12381G1: construct_did_key_bls12381g1,
    BLS12381G1G2: construct_did_key_bls12381g1g2,
}
