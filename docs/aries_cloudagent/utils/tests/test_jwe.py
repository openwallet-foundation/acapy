import json

from unittest import TestCase

from ..jwe import b64url, JweEnvelope, JweRecipient, from_b64url

IV = b"test nonce"
TAG = b"test tag"
AAD = b"test aad"
CIPHERTEXT = b"test ciphertext"
ENC_KEY_1 = b"test enc key 1"
ENC_KEY_2 = b"test enc key 2"
PARAMS = {"alg": "MyAlg"}
UNPROTECTED = {"abc": "ABC"}


class TestJwe(TestCase):
    def test_envelope_load_single_recipient(self):
        protected = PARAMS.copy()
        protected.update(
            {
                # flattened single recipient
                "header": {"def": "DEF"},
                "encrypted_key": b64url(ENC_KEY_1),
            }
        )
        message = {
            "protected": b64url(json.dumps(protected)),
            "unprotected": UNPROTECTED.copy(),
            "iv": b64url(IV),
            "ciphertext": b64url(CIPHERTEXT),
            "tag": b64url(TAG),
            "aad": b64url(AAD),
        }
        loaded = JweEnvelope.deserialize(message)

        assert loaded.protected == PARAMS
        assert loaded.unprotected == UNPROTECTED
        assert loaded.iv == IV
        assert loaded.tag == TAG
        assert loaded.aad == AAD
        assert loaded.combined_aad == loaded.protected_bytes + b"." + b64url(
            AAD
        ).encode("utf-8")
        assert loaded.ciphertext == CIPHERTEXT

        recips = list(loaded.recipients)
        assert len(recips) == 1
        assert recips[0].encrypted_key == ENC_KEY_1
        assert recips[0].header == {"alg": "MyAlg", "abc": "ABC", "def": "DEF"}

    def test_envelope_load_multiple_recipients(self):
        protected = PARAMS.copy()
        protected.update(
            {
                "recipients": [
                    {"header": {"def": "DEF"}, "encrypted_key": b64url(ENC_KEY_1)},
                    {"header": {"ghi": "GHI"}, "encrypted_key": b64url(ENC_KEY_2)},
                ]
            }
        )
        message = {
            "protected": b64url(json.dumps(protected)),
            "unprotected": UNPROTECTED.copy(),
            "iv": b64url(IV),
            "ciphertext": b64url(CIPHERTEXT),
            "tag": b64url(TAG),
            "aad": b64url(AAD),
        }
        loaded = JweEnvelope.deserialize(message)

        assert loaded.protected == PARAMS
        assert loaded.unprotected == UNPROTECTED
        assert loaded.iv == IV
        assert loaded.tag == TAG
        assert loaded.aad == AAD
        assert loaded.combined_aad == loaded.protected_bytes + b"." + b64url(
            AAD
        ).encode("utf-8")
        assert loaded.ciphertext == CIPHERTEXT

        recips = list(loaded.recipients)
        assert len(recips) == 2
        assert recips[0].encrypted_key == ENC_KEY_1
        assert recips[0].header == {"alg": "MyAlg", "abc": "ABC", "def": "DEF"}
        assert recips[1].encrypted_key == ENC_KEY_2
        assert recips[1].header == {"alg": "MyAlg", "abc": "ABC", "ghi": "GHI"}

    def test_envelope_serialize_single_recipient(self):
        env = JweEnvelope(
            unprotected=UNPROTECTED.copy(),
            iv=IV,
            ciphertext=CIPHERTEXT,
            tag=TAG,
            aad=AAD,
            with_protected_recipients=True,
            with_flatten_recipients=True,
        )
        env.add_recipient(JweRecipient(encrypted_key=ENC_KEY_1, header={"def": "DEF"}))
        env.set_protected(PARAMS)
        message = env.to_json()
        loaded = JweEnvelope.from_json(message)

        # check in flattened form
        prot = json.loads(from_b64url(loaded.protected_b64))
        assert "encrypted_key" in prot

        assert loaded.protected == PARAMS
        assert loaded.with_protected_recipients
        assert loaded.with_flatten_recipients
        assert loaded.unprotected == UNPROTECTED
        assert loaded.iv == IV
        assert loaded.tag == TAG
        assert loaded.aad == AAD
        assert loaded.combined_aad == loaded.protected_bytes + b"." + b64url(
            AAD
        ).encode("utf-8")
        assert loaded.ciphertext == CIPHERTEXT

        recips = list(loaded.recipients)
        assert len(recips) == 1
        assert recips[0].encrypted_key == ENC_KEY_1
        assert recips[0].header == {"alg": "MyAlg", "abc": "ABC", "def": "DEF"}

    def test_envelope_serialize_multiple_recipients(self):
        env = JweEnvelope(
            unprotected=UNPROTECTED.copy(),
            iv=IV,
            ciphertext=CIPHERTEXT,
            tag=TAG,
            aad=AAD,
            with_protected_recipients=True,
            with_flatten_recipients=True,
        )
        env.add_recipient(JweRecipient(encrypted_key=ENC_KEY_1, header={"def": "DEF"}))
        env.add_recipient(JweRecipient(encrypted_key=ENC_KEY_2, header={"ghi": "GHI"}))
        env.set_protected(PARAMS)
        message = env.to_json()
        loaded = JweEnvelope.from_json(message)

        assert loaded.protected == PARAMS
        assert loaded.with_protected_recipients
        assert not loaded.with_flatten_recipients
        assert loaded.unprotected == UNPROTECTED
        assert loaded.iv == IV
        assert loaded.tag == TAG
        assert loaded.aad == AAD
        assert loaded.combined_aad == loaded.protected_bytes + b"." + b64url(
            AAD
        ).encode("utf-8")
        assert loaded.ciphertext == CIPHERTEXT

        recips = list(loaded.recipients)
        assert len(recips) == 2
        assert recips[0].encrypted_key == ENC_KEY_1
        assert recips[0].header == {"alg": "MyAlg", "abc": "ABC", "def": "DEF"}
        assert recips[1].encrypted_key == ENC_KEY_2
        assert recips[1].header == {"alg": "MyAlg", "abc": "ABC", "ghi": "GHI"}
