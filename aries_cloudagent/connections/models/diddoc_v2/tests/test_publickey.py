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


from asynctest import TestCase as AsyncTestCase

from .. import PublicKey

from marshmallow.exceptions import ValidationError


class TestPublicKey(AsyncTestCase):
    async def test_deserialize_ok(self):
        pub_key = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#555",
            "type": "RsaVerificationKey2018",
            "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "publicKeyPem": "-----BEGIN PUBLIC X...",
            "usage": "signing",
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

        result = PublicKey.deserialize(pub_key)
        assert result.type == pub_key["type"]
        assert result.id == pub_key["id"]
        assert result.controller == pub_key["controller"]
        assert result.publicKeyPem == pub_key["publicKeyPem"]
        assert result.usage == pub_key["usage"]

    def test_deserialize_wrong_id(self):
        pub_key = {
            "id": "LjgpST2rjsoxYegQDRm7EL#555",
            "type": "RsaVerificationKey2018",
            "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "publicKeyPem": "-----BEGIN PUBLIC X...",
            "usage": "signing",
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

        with self.assertRaises(ValidationError):
            PublicKey.deserialize(pub_key)

    def test_deserialize_missing_type(self):
        pub_key = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#555",
            "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "publicKeyPem": "-----BEGIN PUBLIC X...",
            "usage": "signing",
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

        with self.assertRaises(ValidationError):
            PublicKey.deserialize(pub_key)

    async def test_serialize_ok(self):
        pub_key = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#555",
            "type": "RsaVerificationKey2018",
            "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "publicKeyPem": "-----BEGIN PUBLIC X...",
            "usage": "signing",
        }

        result = PublicKey(
            id=pub_key["id"],
            type=pub_key["type"],
            controller=pub_key["controller"],
            value=pub_key["publicKeyPem"],
            usage=pub_key["usage"],
        )

        assert result.type == pub_key["type"]
        assert result.id == pub_key["id"]
        assert result.controller == pub_key["controller"]
        assert result.publicKeyPem == pub_key["publicKeyPem"]
        assert result.usage == pub_key["usage"]

        serialized_key = result.serialize()

        assert serialized_key == pub_key
