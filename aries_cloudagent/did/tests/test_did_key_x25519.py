from unittest import TestCase

from ...wallet.key_type import X25519
from ...wallet.util import b58_to_bytes
from ..did_key import DIDKey, DID_KEY_RESOLVERS
from .test_dids import DID_X25519_z6LShLeXRTzevtwcfehaGEzCMyL3bNsAeKCwcqwJxyCo63yE

TEST_X25519_BASE58_KEY = "6fUMuABnqSDsaGKojbUF3P7ZkEL3wi2njsDdUWZGNgCU"
TEST_X25519_FINGERPRINT = "z6LShLeXRTzevtwcfehaGEzCMyL3bNsAeKCwcqwJxyCo63yE"
TEST_X25519_DID = f"did:key:{TEST_X25519_FINGERPRINT}"
TEST_X25519_KEY_ID = f"{TEST_X25519_DID}#{TEST_X25519_FINGERPRINT}"
TEST_X25519_PREFIX_BYTES = b"".join([b"\xec\x01", b58_to_bytes(TEST_X25519_BASE58_KEY)])


class TestDIDKey(TestCase):
    def test_x25519_from_public_key(self):
        key_bytes = b58_to_bytes(TEST_X25519_BASE58_KEY)
        did_key = DIDKey.from_public_key(key_bytes, X25519)

        assert did_key.did == TEST_X25519_DID

    def test_x25519_from_public_key_b58(self):
        did_key = DIDKey.from_public_key_b58(TEST_X25519_BASE58_KEY, X25519)

        assert did_key.did == TEST_X25519_DID

    def test_x25519_from_fingerprint(self):
        did_key = DIDKey.from_fingerprint(TEST_X25519_FINGERPRINT)

        assert did_key.did == TEST_X25519_DID
        assert did_key.public_key_b58 == TEST_X25519_BASE58_KEY

    def test_x25519_from_did(self):
        did_key = DIDKey.from_did(TEST_X25519_DID)

        assert did_key.public_key_b58 == TEST_X25519_BASE58_KEY

    def test_x25519_properties(self):
        did_key = DIDKey.from_did(TEST_X25519_DID)

        assert did_key.fingerprint == TEST_X25519_FINGERPRINT
        assert did_key.did == TEST_X25519_DID
        assert did_key.public_key_b58 == TEST_X25519_BASE58_KEY
        assert did_key.public_key == b58_to_bytes(TEST_X25519_BASE58_KEY)
        assert did_key.key_type == X25519
        assert did_key.key_id == TEST_X25519_KEY_ID
        assert did_key.prefixed_public_key == TEST_X25519_PREFIX_BYTES

    def test_x25519_diddoc(self):
        did_key = DIDKey.from_did(TEST_X25519_DID)

        resolver = DID_KEY_RESOLVERS[X25519]

        assert resolver(did_key) == did_key.did_doc

    def test_x25519_resolver(self):
        did_key = DIDKey.from_did(TEST_X25519_DID)
        resolver = DID_KEY_RESOLVERS[X25519]
        did_doc = resolver(did_key)

        # resolved using uniresolver, updated to did v1
        assert did_doc == DID_X25519_z6LShLeXRTzevtwcfehaGEzCMyL3bNsAeKCwcqwJxyCo63yE
