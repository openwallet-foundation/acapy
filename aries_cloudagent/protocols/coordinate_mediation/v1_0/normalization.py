"""Normalization methods used while transitioning to DID:Key method."""
from ....did.did_key import DIDKey
from ....wallet.key_type import ED25519


def normalize_from_did_key(key: str):
    """Normalize Recipient/Routing keys from DID:Key to public keys."""
    if key.startswith("did:key:"):
        return DIDKey.from_did(key).public_key_b58

    return key


def normalize_from_public_key(key: str):
    """Normalize Recipient/Routing keys from public keys to DID:Key."""
    if key.startswith("did:key:"):
        return key

    return DIDKey.from_public_key_b58(key, ED25519).did
