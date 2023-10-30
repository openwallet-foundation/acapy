from unittest import TestCase

from ...wallet.key_type import BLS12381G1, BLS12381G1G2, BLS12381G2
from ...wallet.util import b58_to_bytes
from ..did_key import DIDKey, DID_KEY_RESOLVERS
from .test_dids import (
    DID_BLS12381G1G2_z5TcESXuYUE9aZWYwSdrUEGK1HNQFHyTt4aVpaCTVZcDXQmUheFwfNZmRksaAbBneNm5KyE52SdJeRCN1g6PJmF31GsHWwFiqUDujvasK3wTiDr3vvkYwEJHt7H5RGEKYEp1ErtQtcEBgsgY2DA9JZkHj1J9HZ8MRDTguAhoFtR4aTBQhgnkP4SwVbxDYMEZoF2TMYn3s,
)

TEST_BLS12381G1G2_BASE58_KEY = "AQ4MiG1JKHmM5N4CgkF9uQ484PHN7gXB3ctF4ayL8hT6FdD6rcfFS3ZnMNntYsyJBckfNPf3HL8VU8jzgyT3qX88Yg3TeF2NkG2aZnJDNnXH1jkJStWMxjLw22LdphqAj1rSorsDhHjE8Rtz61bD6FP9aPokQUDVpZ4zXqsXVcxJ7YEc66TTLTTPwQPS7uNM4u2Fs"
TEST_BLS12381G1G2_FINGERPRINT = "z5TcESXuYUE9aZWYwSdrUEGK1HNQFHyTt4aVpaCTVZcDXQmUheFwfNZmRksaAbBneNm5KyE52SdJeRCN1g6PJmF31GsHWwFiqUDujvasK3wTiDr3vvkYwEJHt7H5RGEKYEp1ErtQtcEBgsgY2DA9JZkHj1J9HZ8MRDTguAhoFtR4aTBQhgnkP4SwVbxDYMEZoF2TMYn3s"
TEST_BLS12381G1G2_DID = f"did:key:{TEST_BLS12381G1G2_FINGERPRINT}"

TEST_BLS12381G1_BASE58_KEY = (
    "7BVES4h78wzabPAfMhchXyH5d8EX78S5TtzePH2YkftWcE6by9yj3NTAv9nsyCeYch"
)
TEST_BLS12381G1_FINGERPRINT = (
    "z3tEG5qmJZX29jJSX5kyhDR5YJNnefJFdwTxRqk6zbEPv4Pf2xF12BpmXv9NExxSRFGfxd"
)
TEST_BLS12381G1_DID = f"did:key:{TEST_BLS12381G1_FINGERPRINT}"

TEST_BLS12381G2_BASE58_KEY = "26d2BdqELsXg7ZHCWKL2D5Y2S7mYrpkdhJemSEEvokd4qy4TULJeeU44hYPGKo4x4DbBp5ARzkv1D6xuB3bmhpdpKAXuXtode67wzh9PCtW8kTqQhH19VSiFZkLNkhe9rtf3"
TEST_BLS12381G2_FINGERPRINT = "zUC7LTa4hWtaE9YKyDsMVGiRNqPMN3s4rjBdB3MFi6PcVWReNfR72y3oGW2NhNcaKNVhMobh7aHp8oZB3qdJCs7RebM2xsodrSm8MmePbN25NTGcpjkJMwKbcWfYDX7eHCJjPGM"
TEST_BLS12381G2_DID = f"did:key:{TEST_BLS12381G2_FINGERPRINT}"
TEST_BLS12381G1G2_PREFIX_BYTES = b"".join(
    [b"\xee\x01", b58_to_bytes(TEST_BLS12381G1G2_BASE58_KEY)]
)


# The tests here are a bit quirky because g1g2 is a concatenation of g1 and g2 public key bytes
# but it works with the already existing did key implementation.
class TestDIDKey(TestCase):
    def test_bls12381g1g2_from_public_key(self):
        key_bytes = b58_to_bytes(TEST_BLS12381G1G2_BASE58_KEY)
        did_key = DIDKey.from_public_key(key_bytes, BLS12381G1G2)

        assert did_key.did == TEST_BLS12381G1G2_DID

    def test_bls12381g1g2_from_public_key_b58(self):
        did_key = DIDKey.from_public_key_b58(TEST_BLS12381G1G2_BASE58_KEY, BLS12381G1G2)

        assert did_key.did == TEST_BLS12381G1G2_DID

    def test_bls12381g1g2_from_fingerprint(self):
        did_key = DIDKey.from_fingerprint(TEST_BLS12381G1G2_FINGERPRINT)

        assert did_key.did == TEST_BLS12381G1G2_DID
        assert did_key.public_key_b58 == TEST_BLS12381G1G2_BASE58_KEY

    def test_bls12381g1g2_from_did(self):
        did_key = DIDKey.from_did(TEST_BLS12381G1G2_DID)

        assert did_key.public_key_b58 == TEST_BLS12381G1G2_BASE58_KEY

    def test_bls12381g1g2_properties(self):
        did_key = DIDKey.from_did(TEST_BLS12381G1G2_DID)

        assert did_key.fingerprint == TEST_BLS12381G1G2_FINGERPRINT
        assert did_key.did == TEST_BLS12381G1G2_DID
        assert did_key.public_key_b58 == TEST_BLS12381G1G2_BASE58_KEY
        assert did_key.public_key == b58_to_bytes(TEST_BLS12381G1G2_BASE58_KEY)
        assert did_key.key_type == BLS12381G1G2
        assert did_key.prefixed_public_key == TEST_BLS12381G1G2_PREFIX_BYTES

    def test_bls12381g1g2_diddoc(self):
        did_key = DIDKey.from_did(TEST_BLS12381G1G2_DID)

        resolver = DID_KEY_RESOLVERS[BLS12381G1G2]

        assert resolver(did_key) == did_key.did_doc

    def test_bls12381g1g2_resolver(self):
        did_key = DIDKey.from_did(
            "did:key:z5TcESXuYUE9aZWYwSdrUEGK1HNQFHyTt4aVpaCTVZcDXQmUheFwfNZmRksaAbBneNm5KyE52SdJeRCN1g6PJmF31GsHWwFiqUDujvasK3wTiDr3vvkYwEJHt7H5RGEKYEp1ErtQtcEBgsgY2DA9JZkHj1J9HZ8MRDTguAhoFtR4aTBQhgnkP4SwVbxDYMEZoF2TMYn3s"
        )
        resolver = DID_KEY_RESOLVERS[BLS12381G1G2]
        did_doc = resolver(did_key)

        assert (
            did_doc
            == DID_BLS12381G1G2_z5TcESXuYUE9aZWYwSdrUEGK1HNQFHyTt4aVpaCTVZcDXQmUheFwfNZmRksaAbBneNm5KyE52SdJeRCN1g6PJmF31GsHWwFiqUDujvasK3wTiDr3vvkYwEJHt7H5RGEKYEp1ErtQtcEBgsgY2DA9JZkHj1J9HZ8MRDTguAhoFtR4aTBQhgnkP4SwVbxDYMEZoF2TMYn3s
        )

    def test_bls12381g1g1_to_g1(self):
        g1g2_did = DIDKey.from_did(TEST_BLS12381G1G2_DID)

        # TODO: add easier method to go form g1 <- g1g2 -> g2
        # First 48 bytes is g1 key
        g1_public_key = g1g2_did.public_key[:48]
        g1_did = DIDKey.from_public_key(g1_public_key, BLS12381G1)

        assert g1_did.fingerprint == TEST_BLS12381G1_FINGERPRINT
        assert g1_did.did == TEST_BLS12381G1_DID
        assert g1_did.public_key_b58 == TEST_BLS12381G1_BASE58_KEY
        assert g1_did.public_key == b58_to_bytes(TEST_BLS12381G1_BASE58_KEY)
        assert g1_did.key_type == BLS12381G1

    def test_bls12381g1g1_to_g2(self):
        g1g2_did = DIDKey.from_did(TEST_BLS12381G1G2_DID)

        # TODO: add easier method to go form g1 <- g1g2 -> g2
        # From 48 bytes is g2 key
        g2_public_key = g1g2_did.public_key[48:]
        g2_did = DIDKey.from_public_key(g2_public_key, BLS12381G2)

        assert g2_did.fingerprint == TEST_BLS12381G2_FINGERPRINT
        assert g2_did.did == TEST_BLS12381G2_DID
        assert g2_did.public_key_b58 == TEST_BLS12381G2_BASE58_KEY
        assert g2_did.public_key == b58_to_bytes(TEST_BLS12381G2_BASE58_KEY)
        assert g2_did.key_type == BLS12381G2
