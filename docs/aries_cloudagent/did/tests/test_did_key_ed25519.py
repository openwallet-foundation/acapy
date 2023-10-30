from unittest import TestCase

from ...wallet.key_type import ED25519
from ...wallet.util import b58_to_bytes
from ..did_key import DIDKey, DID_KEY_RESOLVERS
from .test_dids import DID_ED25519_z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th

TEST_ED25519_BASE58_KEY = "8HH5gYEeNc3z7PYXmd54d4x6qAfCNrqQqEB3nS7Zfu7K"
TEST_ED25519_FINGERPRINT = "z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th"
TEST_ED25519_DID = f"did:key:{TEST_ED25519_FINGERPRINT}"
TEST_ED25519_KEY_ID = f"{TEST_ED25519_DID}#{TEST_ED25519_FINGERPRINT}"
TEST_ED25519_PREFIX_BYTES = b"".join(
    [b"\xed\x01", b58_to_bytes(TEST_ED25519_BASE58_KEY)]
)


class TestDIDKey(TestCase):
    def test_ed25519_from_public_key(self):
        key_bytes = b58_to_bytes(TEST_ED25519_BASE58_KEY)
        did_key = DIDKey.from_public_key(key_bytes, ED25519)

        assert did_key.did == TEST_ED25519_DID

    def test_ed25519_from_public_key_b58(self):
        did_key = DIDKey.from_public_key_b58(TEST_ED25519_BASE58_KEY, ED25519)

        assert did_key.did == TEST_ED25519_DID

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
        assert did_key.key_type == ED25519
        assert did_key.key_id == TEST_ED25519_KEY_ID
        assert did_key.prefixed_public_key == TEST_ED25519_PREFIX_BYTES

    def test_ed25519_diddoc(self):
        did_key = DIDKey.from_did(TEST_ED25519_DID)

        resolver = DID_KEY_RESOLVERS[ED25519]

        assert resolver(did_key) == did_key.did_doc

    def test_ed25519_resolver(self):
        did_key = DIDKey.from_did(TEST_ED25519_DID)
        resolver = DID_KEY_RESOLVERS[ED25519]
        did_doc = resolver(did_key)

        # resolved using uniresolver, updated to did v1
        assert did_doc == DID_ED25519_z6MkmjY8GnV5i9YTDtPETC2uUAW6ejw3nk5mXF5yci5ab7th
