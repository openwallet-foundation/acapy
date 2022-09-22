from unittest import TestCase


from ...wallet.key_type import BLS12381G1
from ...wallet.util import b58_to_bytes
from ..did_key import DIDKey, DID_KEY_RESOLVERS
from .test_dids import (
    DID_BLS12381G1_z3tEFALUKUzzCAvytMHX8X4SnsNsq6T5tC5Zb18oQEt1FqNcJXqJ3AA9umgzA9yoqPBeWA,
)

TEST_BLS12381G1_BASE58_KEY = (
    "6FywSzB5BPd7xehCo1G4nYHAoZPMMP3gd4PLnvgA6SsTsogtz8K7RDznqLpFPLZXAE"
)
TEST_BLS12381G1_FINGERPRINT = (
    "z3tEFALUKUzzCAvytMHX8X4SnsNsq6T5tC5Zb18oQEt1FqNcJXqJ3AA9umgzA9yoqPBeWA"
)
TEST_BLS12381G1_DID = f"did:key:{TEST_BLS12381G1_FINGERPRINT}"
TEST_BLS12381G1_KEY_ID = f"{TEST_BLS12381G1_DID}#{TEST_BLS12381G1_FINGERPRINT}"
TEST_BLS12381G1_PREFIX_BYTES = b"".join(
    [b"\xea\x01", b58_to_bytes(TEST_BLS12381G1_BASE58_KEY)]
)


class TestDIDKey(TestCase):
    def test_bls12381g1_from_public_key(self):
        key_bytes = b58_to_bytes(TEST_BLS12381G1_BASE58_KEY)
        did_key = DIDKey.from_public_key(key_bytes, BLS12381G1)

        assert did_key.did == TEST_BLS12381G1_DID

    def test_bls12381g1_from_public_key_b58(self):
        did_key = DIDKey.from_public_key_b58(TEST_BLS12381G1_BASE58_KEY, BLS12381G1)

        assert did_key.did == TEST_BLS12381G1_DID

    def test_bls12381g1_from_fingerprint(self):
        did_key = DIDKey.from_fingerprint(TEST_BLS12381G1_FINGERPRINT)

        assert did_key.did == TEST_BLS12381G1_DID
        assert did_key.public_key_b58 == TEST_BLS12381G1_BASE58_KEY

    def test_bls12381g1_from_did(self):
        did_key = DIDKey.from_did(TEST_BLS12381G1_DID)

        assert did_key.public_key_b58 == TEST_BLS12381G1_BASE58_KEY

    def test_bls12381g1_properties(self):
        did_key = DIDKey.from_did(TEST_BLS12381G1_DID)

        assert did_key.fingerprint == TEST_BLS12381G1_FINGERPRINT
        assert did_key.did == TEST_BLS12381G1_DID
        assert did_key.public_key_b58 == TEST_BLS12381G1_BASE58_KEY
        assert did_key.public_key == b58_to_bytes(TEST_BLS12381G1_BASE58_KEY)
        assert did_key.key_type == BLS12381G1
        assert did_key.key_id == TEST_BLS12381G1_KEY_ID
        assert did_key.prefixed_public_key == TEST_BLS12381G1_PREFIX_BYTES

    def test_bls12381g1_diddoc(self):
        did_key = DIDKey.from_did(TEST_BLS12381G1_DID)

        resolver = DID_KEY_RESOLVERS[BLS12381G1]

        assert resolver(did_key) == did_key.did_doc

    def test_bls12381g1_resolver(self):
        did_key = DIDKey.from_did(TEST_BLS12381G1_DID)
        resolver = DID_KEY_RESOLVERS[BLS12381G1]
        did_doc = resolver(did_key)

        assert (
            did_doc
            == DID_BLS12381G1_z3tEFALUKUzzCAvytMHX8X4SnsNsq6T5tC5Zb18oQEt1FqNcJXqJ3AA9umgzA9yoqPBeWA
        )
