from asynctest import TestCase as AsyncTestCase

from ....wallet.crypto import KeyType
from ..key_pair_record import KeyPairRecord


class TestKeyPairRecord(AsyncTestCase):
    async def test_serde(self):
        rec = KeyPairRecord(
            key_id="d96ff010-8d09-43f2-ae8e-f8a56ac68a88",
            public_key_b58="o1cocewfMSeasDPVYEkbmeEZUan5fM7ix2oWxeZupgVQFqXRsxUFdAjDmxoosqgdnQJruhMYE3q7gx65MMdgtj67UsUJgJsFYX5ruMyZ58pttzKxnJrM2aoAbhqL1rnQWFf",
            private_key_b58="4xPeQ2sVw8S9opkARzeL6SSgygGiq6JQjFViwXL8v2wE",
            key_type=KeyType.BLS12381G2.key_type,
        )
        ser = rec.serialize()
        assert ser["key_id"] == rec.key_id
        assert ser["public_key_b58"] == rec.public_key_b58
        assert ser["private_key_b58"] == rec.private_key_b58
        assert ser["key_type"] == rec.key_type

        assert rec == KeyPairRecord.deserialize(ser)

    async def test_rec_ops(self):
        recs = [
            KeyPairRecord(
                key_id=f"61764d00-8c16-42dc-b1ec-08c0010ad59c-{i}",
                public_key_b58=f"o1cocewfMSeasDPVYEkbmeEZUan5fM7ix2oWxeZupgVQFqXRsxUFdAjDmxoosqgdnQJruhMYE3q7gx65MMdgtj67UsUJgJsFYX5ruMyZ58pttzKxnJrM2aoAbhqL1rnQWFf-{i}",
                private_key_b58=f"4xPeQ2sVw8S9opkARzeL6SSgygGiq6JQjFViwXL8v2wE-{i}",
                key_type=[KeyType.ED25519, KeyType.BLS12381G2][i].key_type,
            )
            for i in range(2)
        ]
        assert recs[0] != recs[1]
        assert recs[0].key_id
        assert recs[0].public_key_b58
        assert recs[0].private_key_b58
        assert recs[0].key_type == KeyType.ED25519.key_type

        assert recs[1].key_id
        assert recs[1].public_key_b58
        assert recs[1].private_key_b58
        assert recs[1].key_type == KeyType.BLS12381G2.key_type