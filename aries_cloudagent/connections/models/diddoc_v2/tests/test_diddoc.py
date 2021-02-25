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
import copy
from aries_cloudagent.connections.models.diddoc_v2 import (
    DIDDoc,
    VerificationMethod,
    Service,
)

from marshmallow.exceptions import ValidationError

from aries_cloudagent.resolver.did import InvalidDIDUrlError

publicKey = {
    "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#3",
    "type": "RsaVerificationKey2018",
    "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
    "publicKeyPem": "-----BEGIN PUBLIC X...",
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
    async def test_create_did_doc(self):
        did = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "service": [service],
            "publicKey": [publicKey],
            "authentication": [publicKey],
        }

        did_doc = DIDDoc(
            id="did:sov:LjgpST2rjsoxYegQDRm7EL",
            service=[Service.deserialize(service)],
            public_key=[VerificationMethod.deserialize(publicKey)],
            authentication=["did:sov:LjgpST2rjsoxYegQDRm7EL#3"],
        )
        assert not did_doc.also_known_as
        assert not did_doc.controller
        assert not did_doc.verification_method
        assert did_doc.authentication[0].serialize() == publicKey
        assert not did_doc.assertion_method
        assert not did_doc.key_agreement
        assert not did_doc.capability_delegation
        assert not did_doc.capability_invocation
        assert did_doc.public_key[0].serialize() == publicKey
        assert did_doc.service[0].serialize() == service

    async def test_create_did_doc_wrong_id(self):

        with self.assertRaises(ValueError):
            did_doc = DIDDoc(id="did:sovLjgpST2rjsoxYegQDRm7EL")

    async def test_update_doc(self):
        did = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "service": [service],
            "publicKey": [publicKey],
            "authentication": [publicKey],
        }
        verification = VerificationMethod.deserialize(publicKey)
        did_doc = DIDDoc(
            id="did:sov:LjgpST2rjsoxYegQDRm7EL",
            service=[Service.deserialize(service)],
            public_key=[verification],
            authentication=["did:sov:LjgpST2rjsoxYegQDRm7EL#3"],
        )

        did_doc.id = "did:sov:LjgpST2rjsoxYegQDRm72"
        verification_keys = (
            "verificationMethod",
            "assertionMethod",
            "keyAgreement",
            "capabilityDelegation",
            "capabilityInvocation",
        )
        for key in verification_keys:
            did_doc.set(verification, True, key)

        # Not upsert active
        with self.assertRaises(ValueError):
            did_doc.set(verification, False, "verificationMethod")

        assert did_doc.id == "did:sov:LjgpST2rjsoxYegQDRm72"
        assert not did_doc.also_known_as
        assert not did_doc.controller
        assert did_doc.verification_method[0].serialize() == publicKey
        assert did_doc.authentication[0].serialize() == publicKey
        assert did_doc.assertion_method[0].serialize() == publicKey
        assert did_doc.key_agreement[0].serialize() == publicKey
        assert did_doc.capability_delegation[0].serialize() == publicKey
        assert did_doc.capability_invocation[0].serialize() == publicKey
        assert did_doc.public_key[0].serialize() == publicKey
        assert did_doc.service[0].serialize() == service

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
        assert len(result.public_key) == 1
        assert result.public_key[0].serialize() == publicKey
        assert len(result.authentication) == 1
        assert result.authentication[0].serialize() == publicKey

    async def test_deserialize_wrong_id(self):
        did = {
            "id": "dd:sov:LjgpST2rjsoxYegQDRm7EL",
            "service": [service],
            "publicKey": [publicKey],
            "authentication": [publicKey],
        }

        with self.assertRaises(ValidationError):
            DIDDoc.deserialize(did)

    async def test_deserialize_wrong_service(self):
        service2 = copy.copy(service)
        service2.pop("id")

        did = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "service": [service2],
            "publicKey": [publicKey],
            "authentication": [publicKey],
        }

        with self.assertRaises(ValidationError):
            DIDDoc.deserialize(did)

    async def test_deserialize_wrong_publicKey(self):
        publicKey2 = copy.copy(publicKey)
        publicKey2.pop("id")

        did = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "service": [service],
            "publicKey": [publicKey2],
            "authentication": [publicKey],
        }

        with self.assertRaises(ValidationError):
            DIDDoc.deserialize(did)

    async def test_deserialize_missing_id(self):
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

        service2 = copy.copy(service)
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
        publicKey_instance = VerificationMethod.deserialize(publicKey)
        did_instance = DIDDoc(id=did["id"], public_key=[publicKey_instance])
        assert did_instance.id == did["id"]
        assert len(did_instance.public_key) == 1
        assert did_instance.public_key[0].serialize() == publicKey
        assert did_instance.public_key[0] == publicKey_instance

        publicKey2 = copy.copy(publicKey)
        publicKey2["id"] = "did:sov:LjgpST2rjsoxYegQDRm7EL#5"
        publicKey_instance2 = VerificationMethod.deserialize(publicKey2)
        did_instance.set(publicKey_instance2)
        assert len(did_instance.public_key) == 2

    async def test_serialize_ok(self):
        did = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "service": [service],
            "publicKey": [publicKey],
            "authentication": [publicKey],
        }

        result = DIDDoc.deserialize(did).serialize()

        assert result["id"] == did["id"]
        assert len(result["service"]) == 1
        assert result["service"][0] == service
        assert len(result["publicKey"]) == 1
        assert result["publicKey"][0] == publicKey
        assert len(result["authentication"]) == 1
        assert result["authentication"][0] == publicKey
        assert result["@context"] == "https://w3id.org/did/v1"

    async def test_dereference_ok(self):
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
        assert isinstance(service_instance, Service)
        assert isinstance(publicKey_instance, VerificationMethod)

    async def test_dereference_bad_id(self):
        did = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "service": [service],
            "publicKey": [publicKey],
            "authentication": [publicKey],
        }

        result = DIDDoc.deserialize(did)
        with self.assertRaises(InvalidDIDUrlError):
            result.dereference("did:sovLjgpST2rjsoxYegQDRm7EL#2")

    async def test_dereference_missing_id(self):
        did = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "service": [service],
            "publicKey": [publicKey],
            "authentication": [publicKey],
        }

        result = DIDDoc.deserialize(did)

        assert not result.dereference("did:sov:LjgpST2rjsoxYegQDRm7EL#10")
