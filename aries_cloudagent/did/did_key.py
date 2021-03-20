from multicodec.multicodec import add_prefix, get_codec, remove_prefix
from varint import encode

from ..wallet.crypto import KeyType, ed25519_pk_to_curve25519
from ..wallet.util import b58_to_bytes, bytes_to_b58


# TODO: use did resolver did doc class
def resolve_did_key_ed25519(did_key: "DIDKey") -> dict:
    curve25519 = ed25519_pk_to_curve25519(did_key.public_key)
    # TODO: reuse already existing fingerprint methods
    # TODO: update once https://github.com/multiformats/py-multicodec/pull/14 is merged
    curve25519_fingerprint = "z" + bytes_to_b58(b"".join([b"\xec\x01", curve25519]))

    return {
        "@context": "https://w3id.org/did/v1",
        "id": did_key.did,
        "verificationMethod": [
            {
                "id": did_key.key_id,
                "type": "Ed25519VerificationKey2018",
                "controller": did_key.did,
                "publicKeyBase58": did_key.public_key_b58,
            }
        ],
        "authentication": [did_key.key_id],
        "assertionMethod": [did_key.key_id],
        "capabilityDelegation": [did_key.key_id],
        "capabilityInvocation": [did_key.key_id],
        "keyAgreement": [
            {
                "id": f"{did_key.did}#{curve25519_fingerprint}",
                "type": "X25519KeyAgreementKey2019",
                "controller": did_key.did,
                "publicKeyBase58": bytes_to_b58(curve25519),
            }
        ],
    }


DID_KEY_RESOLVERS = {KeyType.ED25519: resolve_did_key_ed25519}


class DIDKey:
    _key_type: KeyType
    _public_key: bytes

    def __init__(self, public_key: bytes, key_type: KeyType) -> None:
        self._public_key = public_key
        self._key_type = key_type

    @classmethod
    def from_public_key(cls, public_key: bytes, key_type: str) -> "DIDKey":
        return cls(public_key, key_type)

    @classmethod
    def from_public_key_b58(cls, public_key: str, key_type: str) -> "DIDKey":
        public_key_bytes = b58_to_bytes(public_key)
        return cls.from_public_key(public_key_bytes, key_type)

    @classmethod
    def from_fingerprint(cls, fingerprint: str) -> "DIDKey":
        assert fingerprint[0] == "z"
        key_bytes_with_prefix = b58_to_bytes(fingerprint[1:])
        public_key_bytes = remove_prefix(key_bytes_with_prefix)

        multicodec_name = get_codec(key_bytes_with_prefix)
        key_type = KeyType.from_multicodec_name(multicodec_name)

        return cls(public_key_bytes, key_type)

    @classmethod
    def from_did(cls, did: str) -> "DIDKey":
        did_parts = did.split("#")
        _, fingerprint = did_parts[0].split("did:key:")

        return cls.from_fingerprint(fingerprint)

    @property
    def fingerprint(self) -> str:
        prefixed_key_bytes = add_prefix(self.key_type.multicodec_name, self.public_key)

        return f"z{bytes_to_b58(prefixed_key_bytes)}"

    @property
    def did(self) -> str:
        return f"did:key:{self.fingerprint}"

    @property
    def did_doc(self) -> dict:
        resolver = DID_KEY_RESOLVERS[self.key_type]
        return resolver(self)

    @property
    def public_key(self) -> bytes:
        return self._public_key

    @property
    def public_key_b58(self) -> str:
        return bytes_to_b58(self.public_key)

    @property
    def key_type(self) -> KeyType:
        return self._key_type

    @property
    def key_id(self) -> str:
        return f"{self.did}#{self.fingerprint}"
