"""
DID Document tests.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json

from asynctest import TestCase as AsyncTestCase

from aries_cloudagent.connections.models.diddoc_v2 import (
    VerificationMethod,
    PublicKeyType,
)

from marshmallow.exceptions import ValidationError

TEST_ID = "did:sov:LjgpST2rjsoxYegQDRm7EL#555"


class TestPublicKey(AsyncTestCase):
    def test_public_key_type(self):
        key_type = PublicKeyType.get("RsaVerificationKey2018")
        assert key_type == PublicKeyType.RSA_SIG_2018
        assert key_type.specification("test") == {"publicKeyPem": "test"}
        key_type = PublicKeyType.get("Noexistingtype")
        assert not key_type

    def test_create_verification(self):
        key = "ZXd1ZXduZXduaXV3ZWg3d2V3ZW5q"
        v_method = VerificationMethod(
            id=TEST_ID,
            type=PublicKeyType.ED25519_SIG_2018,
            value=key,
            controller=TEST_ID,
        )
        print(v_method)
        assert v_method.value == key
        assert v_method.type == PublicKeyType.ED25519_SIG_2018.ver_type
        assert v_method.controller == TEST_ID
        assert v_method.id == TEST_ID
        return v_method

    def test_update_verification(self):
        key = "-----BEGIN PUBLIC X..."
        key_hex = "0361f286ada2a6b2c74bc6ed44a71ef59fb9dd15eca9283cbe5608aeb516730f33"
        new_id = "{}5".format(TEST_ID)
        type_jwk = "EcdsaSecp256k1RecoveryMethod2020"

        key_jwk = {
            "kty": "EC",
            "crv": "secp256k1",
            "kid": "JUvpllMEYUZ2joO59UNui_XYDqxVqiFLLAJ8klWuPBw",
            "x": "dWCvM4fTdeM0KmloF57zxtBPXTOythHPMm1HCLrdd3A",
            "y": "36uMVGM7hnw-N6GnjFcihWE3SkrhMLzzLCdPMXPEXlA",
        }

        v_method = self.test_create_verification()
        v_method.id = new_id
        v_method.type = PublicKeyType.RSA_SIG_2018
        v_method.controller = new_id
        v_method.value = key
        v_method.authn = True
        v_method.usage = "1"
        assert v_method.id == new_id
        assert v_method.type == PublicKeyType.RSA_SIG_2018.ver_type
        assert v_method.controller == new_id
        assert v_method.value == key
        assert v_method.authn
        assert v_method.usage == "1"

        v_method.type = PublicKeyType.EDDSA_SA_SIG_SECP256K1
        v_method.value = key_hex
        assert v_method.type == PublicKeyType.EDDSA_SA_SIG_SECP256K1.ver_type
        assert v_method.value == key_hex

        v_method.type = type_jwk
        v_method.value = key_jwk
        assert v_method.type == type_jwk
        assert v_method.value == key_jwk
        v_method.value = json.dumps(key_jwk)
        assert v_method.value == key_jwk

    def test_deserialize_ok(self):
        pub_key = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#555",
            "type": "RsaVerificationKey2018",
            "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "publicKeyPem": "-----BEGIN PUBLIC X...",
            "publicKeyBase58": "ZXd1ZXduZXduaXV3ZWg3d2V3ZW5q",
            "publicKeyHex": "0361f286ada2a6b2c74bc6ed44a71ef59fb9dd15eca9283cbe5608aeb516730f33",
            "publicKeyJwk": {
                "kty": "EC",
                "crv": "secp256k1",
                "kid": "JUvpllMEYUZ2joO59UNui_XYDqxVqiFLLAJ8klWuPBw",
                "x": "dWCvM4fTdeM0KmloF57zxtBPXTOythHPMm1HCLrdd3A",
                "y": "36uMVGM7hnw-N6GnjFcihWE3SkrhMLzzLCdPMXPEXlA",
            },
        }

        result = VerificationMethod.deserialize(pub_key)
        assert result.type == pub_key["type"]
        assert result.id == pub_key["id"]
        assert result.controller == pub_key["controller"]
        assert result.publicKeyPem == pub_key["publicKeyPem"]

    def test_deserialize_wrong_id(self):
        with self.assertRaises(ValidationError):
            pub_key = {
                "id": "LjgpST2rjsoxYegQDRm7EL#555",
                "type": "RsaVerificationKey2018",
                "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
                "publicKeyPem": "-----BEGIN PUBLIC X...",
                "publicKeyBase58": "ZXd1ZXduZXduaXV3ZWg3d2V3ZW5q",
                "publicKeyHex": "0361f286ada2a6b2c74bc6ed44a71ef59fb9dd15eca9283cbe5608aeb516730f33",
                "publicKeyJwk": {
                    "kty": "EC",
                    "crv": "secp256k1",
                    "kid": "JUvpllMEYUZ2joO59UNui_XYDqxVqiFLLAJ8klWuPBw",
                    "x": "dWCvM4fTdeM0KmloF57zxtBPXTOythHPMm1HCLrdd3A",
                    "y": "36uMVGM7hnw-N6GnjFcihWE3SkrhMLzzLCdPMXPEXlA",
                },
            }

            VerificationMethod.deserialize(pub_key)

    def test_deserialize_missing_type(self):
        with self.assertRaises(ValidationError):
            pub_key = {
                "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#555",
                "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
                "publicKeyPem": "-----BEGIN PUBLIC X...",
                "publicKeyBase58": "ZXd1ZXduZXduaXV3ZWg3d2V3ZW5q",
                "publicKeyHex": "0361f286ada2a6b2c74bc6ed44a71ef59fb9dd15eca9283cbe5608aeb516730f33",
                "publicKeyJwk": {
                    "kty": "EC",
                    "crv": "secp256k1",
                    "kid": "JUvpllMEYUZ2joO59UNui_XYDqxVqiFLLAJ8klWuPBw",
                    "x": "dWCvM4fTdeM0KmloF57zxtBPXTOythHPMm1HCLrdd3A",
                    "y": "36uMVGM7hnw-N6GnjFcihWE3SkrhMLzzLCdPMXPEXlA",
                },
            }

            VerificationMethod.deserialize(pub_key)

    def test_serialize_ok(self):
        pub_key = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#555",
            "type": "RsaVerificationKey2018",
            "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "publicKeyPem": "-----BEGIN PUBLIC X...",
        }

        result = VerificationMethod(
            id=pub_key["id"],
            type=pub_key["type"],
            controller=pub_key["controller"],
            value=pub_key["publicKeyPem"],
        )

        assert result.type == pub_key["type"]
        assert result.id == pub_key["id"]
        assert result.controller == pub_key["controller"]
        assert result.publicKeyPem == pub_key["publicKeyPem"]

        serialized_key = result.serialize()

        assert serialized_key == pub_key
