from unittest import TestCase

from ...wallet.key_type import P256
from ...wallet.util import b58_to_bytes
from ..did_key import DID_KEY_RESOLVERS, DIDKey
from .test_dids import DID_P256_zDnaerDaTF5BXEavCrfRZEk316dpbLsfPDZ3WJ5hRTPFU2169

TEST_P256_BASE58_KEY = "23FF9c3MrW7NkEW6uNDvdSKQMJ4YFTBXNMEPytZfYeE33"
TEST_P256_FINGERPRINT = "zDnaerDaTF5BXEavCrfRZEk316dpbLsfPDZ3WJ5hRTPFU2169"
TEST_P256_DID = f"did:key:{TEST_P256_FINGERPRINT}"
TEST_P256_KEY_ID = f"{TEST_P256_DID}#{TEST_P256_FINGERPRINT}"
TEST_P256_PREFIX_BYTES = b"".join([b"\x80\x24", b58_to_bytes(TEST_P256_BASE58_KEY)])


class TestDIDKey(TestCase):
    def test_p256_from_public_key(self):
        key_bytes = b58_to_bytes(TEST_P256_BASE58_KEY)
        did_key = DIDKey.from_public_key(key_bytes, P256)

        assert did_key.did == TEST_P256_DID

    def test_p256_from_public_key_b58(self):
        did_key = DIDKey.from_public_key_b58(TEST_P256_BASE58_KEY, P256)

        assert did_key.did == TEST_P256_DID

    def test_p256_from_fingerprint(self):
        did_key = DIDKey.from_fingerprint(TEST_P256_FINGERPRINT)

        assert did_key.did == TEST_P256_DID
        assert did_key.public_key_b58 == TEST_P256_BASE58_KEY

    def test_p256_from_did(self):
        did_key = DIDKey.from_did(TEST_P256_DID)

        assert did_key.public_key_b58 == TEST_P256_BASE58_KEY

    def test_p256_properties(self):
        did_key = DIDKey.from_did(TEST_P256_DID)

        assert did_key.fingerprint == TEST_P256_FINGERPRINT
        assert did_key.did == TEST_P256_DID
        assert did_key.public_key_b58 == TEST_P256_BASE58_KEY
        assert did_key.public_key == b58_to_bytes(TEST_P256_BASE58_KEY)
        assert did_key.key_type == P256
        assert did_key.key_id == TEST_P256_KEY_ID
        assert did_key.prefixed_public_key == TEST_P256_PREFIX_BYTES

    def test_p256_diddoc(self):
        did_key = DIDKey.from_did(TEST_P256_DID)

        resolver = DID_KEY_RESOLVERS[P256]

        assert resolver(did_key) == did_key.did_doc

    def test_p256_resolver(self):
        did_key = DIDKey.from_did(TEST_P256_DID)
        resolver = DID_KEY_RESOLVERS[P256]
        did_doc = resolver(did_key)

        assert did_doc == DID_P256_zDnaerDaTF5BXEavCrfRZEk316dpbLsfPDZ3WJ5hRTPFU2169
