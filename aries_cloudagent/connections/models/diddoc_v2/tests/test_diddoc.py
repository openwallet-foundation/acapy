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

from .. import DIDDoc, PublicKey, Service

from marshmallow.exceptions import ValidationError

publicKey = {
    "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#3",
    "type": "RsaVerificationKey2018",
    "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
    "publicKeyPem": "-----BEGIN PUBLIC X...",
    "usage": "signing",
}

service = {
    "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#2",
    "type": "one",
    "priority": 1,
    "recipientKeys": ["did:sov:LjgpST2rjsoxYegQDRm7EL#keys-1"],
    "routingKeys": ["did:sov:LjgpST2rjsoxYegQDRm7EL#keys-4"],
    "serviceEndpoint": "LjgpST2rjsoxYegQDRm7EL;2",
}


class TestDIDDoc(AsyncTestCase):
    async def test_deserialize_ok(self):
        did = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "service": [service],
            "publicKey": [publicKey],
            "authentication": [publicKey],
        }

        result = DIDDoc.deserialize(did)
        assert result.id == did["id"]
        assert len(result.service) == 1
        assert result.service[0].serialize() == service
        assert len(result.publicKey) == 1
        assert result.publicKey[0].serialize() == publicKey
        assert len(result.authentication) == 1
        assert result.authentication[0].serialize() == publicKey

    def test_deserialize_wrong_id(self):
        did = {
            "id": "dd:sov:LjgpST2rjsoxYegQDRm7EL",
            "service": [service],
            "publicKey": [publicKey],
            "authentication": [publicKey],
        }

        with self.assertRaises(ValidationError):
            DIDDoc.deserialize(did)

    def test_deserialize_wrong_service(self):
        service2 = service
        service2.pop("id")

        did = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "service": [service2],
            "publicKey": [publicKey],
            "authentication": [publicKey],
        }

        with self.assertRaises(ValidationError):
            DIDDoc.deserialize(did)

    def test_deserialize_wrong_publicKey(self):
        publicKey2 = publicKey
        publicKey2.pop("id")

        did = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "service": [service],
            "publicKey": [publicKey2],
            "authentication": [publicKey],
        }

        with self.assertRaises(ValidationError):
            DIDDoc.deserialize(did)

    def test_deserialize_missing_id(self):
        did = {
            "service": [service],
            "publicKey": [publicKey],
            "authentication": [publicKey],
        }

        with self.assertRaises(ValidationError):
            DIDDoc.deserialize(did)

    async def test_add_new_service(self):
        did = {"id": "did:sov:LjgpST2rjsoxYegQDRm7EL", "service": [service]}
        service_instance = Service.deserialize(service)
        did_instance = DIDDoc(id=did["id"], service=[service_instance])
        assert did_instance.id == did["id"]
        assert len(did_instance.service) == 1
        assert did_instance.service[0].serialize() == service
        assert did_instance.service[0] == service_instance

        service2 = service
        service2["id"] = "did:sov:LjgpST2rjsoxYegQDRm7EL#5"
        service_instance2 = Service.deserialize(service2)
        did_instance.set(service_instance2)
        assert len(did_instance.service) == 2

    async def test_update_service(self):
        did = {"id": "did:sov:LjgpST2rjsoxYegQDRm7EL", "service": [service]}
        service_instance = Service.deserialize(service)
        did_instance = DIDDoc(id=did["id"], service=[service_instance])
        assert did_instance.id == did["id"]
        assert len(did_instance.service) == 1
        assert did_instance.service[0].serialize() == service
        assert did_instance.service[0] == service_instance

        did_instance.set(service_instance, upsert=True)
        assert len(did_instance.service) == 1
        assert did_instance.service[0].serialize() == service
        assert did_instance.service[0] == service_instance

    async def test_add_new_verification_method(self):
        did = {"id": "did:sov:LjgpST2rjsoxYegQDRm7EL", "publicKey": [publicKey]}
        publicKey_instance = PublicKey.deserialize(publicKey)
        did_instance = DIDDoc(id=did["id"], publicKey=[publicKey_instance])
        assert did_instance.id == did["id"]
        assert len(did_instance.publicKey) == 1
        assert did_instance.publicKey[0].serialize() == publicKey
        assert did_instance.publicKey[0] == publicKey_instance

        publicKey2 = publicKey
        publicKey2["id"] = "did:sov:LjgpST2rjsoxYegQDRm7EL#5"
        publicKey_instance2 = PublicKey.deserialize(publicKey2)
        did_instance.set(publicKey_instance2)
        assert len(did_instance.publicKey) == 2

    async def test_add_new_verification_method(self):
        did = {"id": "did:sov:LjgpST2rjsoxYegQDRm7EL", "publicKey": [publicKey]}
        publicKey_instance = PublicKey.deserialize(publicKey)
        did_instance = DIDDoc(id=did["id"], publicKey=[publicKey_instance])
        assert did_instance.id == did["id"]
        assert len(did_instance.publicKey) == 1
        assert did_instance.publicKey[0].serialize() == publicKey
        assert did_instance.publicKey[0] == publicKey_instance

        publicKey2 = publicKey
        publicKey2["id"] = "did:sov:LjgpST2rjsoxYegQDRm7EL#5"
        publicKey_instance2 = PublicKey.deserialize(publicKey2)
        did_instance.set(publicKey_instance2)
        assert len(did_instance.publicKey) == 2

    async def test_add_new_verification_method(self):
        did = {"id": "did:sov:LjgpST2rjsoxYegQDRm7EL", "publicKey": [publicKey]}
        publicKey_instance = PublicKey.deserialize(publicKey)
        did_instance = DIDDoc(id=did["id"], publicKey=[publicKey_instance])
        assert did_instance.id == did["id"]
        assert len(did_instance.publicKey) == 1
        assert did_instance.publicKey[0].serialize() == publicKey
        assert did_instance.publicKey[0] == publicKey_instance

        publicKey2 = publicKey
        publicKey2["id"] = "did:sov:LjgpST2rjsoxYegQDRm7EL#5"
        publicKey_instance2 = PublicKey.deserialize(publicKey2)
        did_instance.set(publicKey_instance2)
        assert len(did_instance.publicKey) == 2

    async def test_deserialize_ok(self):
        did = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "service": [service],
            "publicKey": [publicKey],
            "authentication": [publicKey],
        }

        result = DIDDoc.deserialize(did)

        service_instance = result.dereference("did:sov:LjgpST2rjsoxYegQDRm7EL#2")
        publicKey_instance = result.dereference("did:sov:LjgpST2rjsoxYegQDRm7EL#3")
        assert service_instance.serialize() == service
        assert publicKey_instance.serialize() == publicKey
