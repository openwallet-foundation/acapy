from unittest import TestCase

from ...wallet.crypto import KeyType
from ...wallet.util import b58_to_bytes
from ..did_key import DIDKey, DID_KEY_RESOLVERS

TEST_ED25519_BASE58_KEY = "8HH5gYEeNc3z7PYXmd54d4x6qAfCNrqQqEB3nS7Zfu7K"
TEST_ED25519_FINGERPRINT = "z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th"
TEST_ED25519_DID = f"did:key:{TEST_ED25519_FINGERPRINT}"
TEST_ED25519_KEY_ID = f"{TEST_ED25519_DID}#{TEST_ED25519_FINGERPRINT}"


class TestDIDKey(TestCase):
    def test_ed25519_from_public_key(self):
        key_bytes = b58_to_bytes(TEST_ED25519_BASE58_KEY)
        did_key = DIDKey.from_public_key(key_bytes, KeyType.ED25519)

        assert did_key.did == TEST_ED25519_DID

    def test_ed25519_from_public_key_b58(self):
        did_key = DIDKey.from_public_key_b58(
            "8HH5gYEeNc3z7PYXmd54d4x6qAfCNrqQqEB3nS7Zfu7K", KeyType.ED25519
        )

        assert did_key.did == "did:key:z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th"

    def test_ed25519_from_fingerprint(self):
        did_key = DIDKey.from_fingerprint(TEST_ED25519_FINGERPRINT)

        assert did_key.did == TEST_ED25519_DID
        assert did_key.public_key_b58 == TEST_ED25519_BASE58_KEY

    def test_ed25519_from_did(self):
        did_key = DIDKey.from_did(TEST_ED25519_DID)

        assert did_key.public_key_b58 == TEST_ED25519_BASE58_KEY

    def test_ed25519_properties(self):
        did_key = DIDKey.from_did(TEST_ED25519_DID)

        assert did_key.fingerprint == TEST_ED25519_FINGERPRINT
        assert did_key.did == TEST_ED25519_DID
        assert did_key.public_key_b58 == TEST_ED25519_BASE58_KEY
        assert did_key.public_key == b58_to_bytes(TEST_ED25519_BASE58_KEY)
        assert did_key.key_type == KeyType.ED25519
        assert did_key.key_id == TEST_ED25519_KEY_ID

    def test_ed25519_diddoc(self):
        did_key = DIDKey.from_did(TEST_ED25519_DID)

        resolver = DID_KEY_RESOLVERS[KeyType.ED25519]

        assert resolver(did_key) == did_key.did_doc

    def test_ed25519_resolver(self):
        did_key = DIDKey.from_did(TEST_ED25519_DID)
        resolver = DID_KEY_RESOLVERS[KeyType.ED25519]
        did_doc = resolver(did_key)

        # resolved using uniresolver, updated to did v1
        expected = {
            "@context": "https://w3id.org/did/v1",
            "id": "did:key:z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th",
            "verificationMethod": [
                {
                    "id": "did:key:z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th#z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th",
                    "type": "Ed25519VerificationKey2018",
                    "controller": "did:key:z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th",
                    "publicKeyBase58": "8HH5gYEeNc3z7PYXmd54d4x6qAfCNrqQqEB3nS7Zfu7K",
                }
            ],
            "authentication": [
                "did:key:z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th#z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th"
            ],
            "assertionMethod": [
                "did:key:z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th#z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th"
            ],
            "capabilityDelegation": [
                "did:key:z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th#z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th"
            ],
            "capabilityInvocation": [
                "did:key:z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th#z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th"
            ],
            "keyAgreement": [
                {
                    "id": "did:key:z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th#z6LShpNhGwSupbB7zjuivH156vhLJBDDzmQtA4BY9S94pe1K",
                    "type": "X25519KeyAgreementKey2019",
                    "controller": "did:key:z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th",
                    "publicKeyBase58": "79CXkde3j8TNuMXxPdV7nLUrT2g7JAEjH5TreyVY7GEZ",
                }
            ],
        }

        assert did_doc == expected
