from unittest import TestCase

from ...wallet.key_type import BLS12381G2
from ...wallet.util import b58_to_bytes
from ..did_key import DIDKey, DID_KEY_RESOLVERS
from .test_dids import (
    DID_BLS12381G2_zUC71nmwvy83x1UzNKbZbS7N9QZx8rqpQx3Ee3jGfKiEkZngTKzsRoqobX6wZdZF5F93pSGYYco3gpK9tc53ruWUo2tkBB9bxPCFBUjq2th8FbtT4xih6y6Q1K9EL4Th86NiCGT,
)

TEST_BLS12381G2_BASE58_KEY = "mxE4sHTpbPcmxNviRVR9r7D2taXcNyVJmf9TBUFS1gRt3j3Ej9Seo59GQeCzYwbQgDrfWCwEJvmBwjLvheAky5N2NqFVzk4kuq3S8g4Fmekai4P622vHqWjFrsioYYDqhf9"
TEST_BLS12381G2_FINGERPRINT = "zUC71nmwvy83x1UzNKbZbS7N9QZx8rqpQx3Ee3jGfKiEkZngTKzsRoqobX6wZdZF5F93pSGYYco3gpK9tc53ruWUo2tkBB9bxPCFBUjq2th8FbtT4xih6y6Q1K9EL4Th86NiCGT"
TEST_BLS12381G2_DID = f"did:key:{TEST_BLS12381G2_FINGERPRINT}"
TEST_BLS12381G2_KEY_ID = f"{TEST_BLS12381G2_DID}#{TEST_BLS12381G2_FINGERPRINT}"
TEST_BLS12381G2_PREFIX_BYTES = b"".join(
    [b"\xeb\x01", b58_to_bytes(TEST_BLS12381G2_BASE58_KEY)]
)


class TestDIDKey(TestCase):
    def test_bls12381g2_from_public_key(self):
        key_bytes = b58_to_bytes(TEST_BLS12381G2_BASE58_KEY)
        did_key = DIDKey.from_public_key(key_bytes, BLS12381G2)

        assert did_key.did == TEST_BLS12381G2_DID

    def test_bls12381g2_from_public_key_b58(self):
        did_key = DIDKey.from_public_key_b58(TEST_BLS12381G2_BASE58_KEY, BLS12381G2)

        assert did_key.did == TEST_BLS12381G2_DID

    def test_bls12381g2_from_fingerprint(self):
        did_key = DIDKey.from_fingerprint(TEST_BLS12381G2_FINGERPRINT)

        assert did_key.did == TEST_BLS12381G2_DID
        assert did_key.public_key_b58 == TEST_BLS12381G2_BASE58_KEY

    def test_bls12381g2_from_did(self):
        did_key = DIDKey.from_did(TEST_BLS12381G2_DID)

        assert did_key.public_key_b58 == TEST_BLS12381G2_BASE58_KEY

    def test_bls12381g2_properties(self):
        did_key = DIDKey.from_did(TEST_BLS12381G2_DID)

        assert did_key.fingerprint == TEST_BLS12381G2_FINGERPRINT
        assert did_key.did == TEST_BLS12381G2_DID
        assert did_key.public_key_b58 == TEST_BLS12381G2_BASE58_KEY
        assert did_key.public_key == b58_to_bytes(TEST_BLS12381G2_BASE58_KEY)
        assert did_key.key_type == BLS12381G2
        assert did_key.key_id == TEST_BLS12381G2_KEY_ID
        assert did_key.prefixed_public_key == TEST_BLS12381G2_PREFIX_BYTES

    def test_bls12381g2_diddoc(self):
        did_key = DIDKey.from_did(TEST_BLS12381G2_DID)

        resolver = DID_KEY_RESOLVERS[BLS12381G2]

        assert resolver(did_key) == did_key.did_doc

    def test_bls12381g2_resolver(self):
        did_key = DIDKey.from_did(TEST_BLS12381G2_DID)
        resolver = DID_KEY_RESOLVERS[BLS12381G2]
        did_doc = resolver(did_key)

        assert (
            did_doc
            == DID_BLS12381G2_zUC71nmwvy83x1UzNKbZbS7N9QZx8rqpQx3Ee3jGfKiEkZngTKzsRoqobX6wZdZF5F93pSGYYco3gpK9tc53ruWUo2tkBB9bxPCFBUjq2th8FbtT4xih6y6Q1K9EL4Th86NiCGT
        )
