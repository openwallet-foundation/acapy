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
import json
from aries_cloudagent.connections.models.diddoc_v2 import (
    DIDDoc,
    AntiquatedDIDDoc,
    VerificationMethod,
    Service,
)

from marshmallow.exceptions import ValidationError

from aries_cloudagent.resolver.did import InvalidDIDUrlError, DIDUrl

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
    "recipientKeys": ["did:sov:LjgpST2rjsoxYegQDRm7EL#3"],
    "routingKeys": ["did:sov:LjgpST2rjsoxYegQDRm7EL#3"],
    "serviceEndpoint": "LjgpST2rjsoxYegQDRm7EL;2",
}

service_key = {
    "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#8",
    "type": "one",
    "priority": 1,
    "routingKeys": [publicKey],
    "serviceEndpoint": "LjgpST2rjsoxYegQDRm7EL;2",
}


class TestDIDDoc(AsyncTestCase):
    async def test_create_did_doc(self):
        did_doc = DIDDoc(
            id="did:sov:LjgpST2rjsoxYegQDRm7EL",
            service=[Service.deserialize(service), Service.deserialize(service_key)],
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
        assert did_doc.service[1].serialize() == service_key

    async def test_create_antiquated_did_doc(self):
        did_doc = AntiquatedDIDDoc("LjgpST2rjsoxYegQDRm7EL")
        assert not did_doc.also_known_as
        assert not did_doc.controller
        assert not did_doc.verification_method
        assert not did_doc.authentication
        assert not did_doc.assertion_method
        assert not did_doc.key_agreement
        assert not did_doc.capability_delegation
        assert not did_doc.capability_invocation
        assert not did_doc.public_key
        assert not did_doc.service
        assert did_doc.id == "did:sov:LjgpST2rjsoxYegQDRm7EL"
        did_doc.add_service(
            type="service2",
            endpoint="LjgpST2rjsoxYegQDRm7EL;2",
            ident="2",
            priority=4,
            upsert=True,
        )

        did_doc.add_verification_method(
            type=publicKey["type"],
            controller=publicKey["controller"],
            value=publicKey["publicKeyPem"],
            ident="3",
        )

        assert did_doc.public_key
        assert did_doc.service
        assert did_doc.public_key[0].id == "did:sov:LjgpST2rjsoxYegQDRm7EL#3"
        assert did_doc.service[0].id == "did:sov:LjgpST2rjsoxYegQDRm7EL#2"

    async def test_create_inconsistent_did_doc(self):
        serv_copy = copy.copy(service)
        serv_copy["recipientKeys"] = ["did:sov:LjgpST2rjsoxYegQDRm7EL#99"]
        with self.assertRaises(ValueError):
            DIDDoc(
                id="did:sov:LjgpST2rjsoxYegQDRm7EL",
                service=[
                    Service.deserialize(serv_copy),
                    Service.deserialize(service_key),
                ],
                public_key=[VerificationMethod.deserialize(publicKey)],
                authentication=["did:sov:LjgpST2rjsoxYegQDRm7EL#3"],
            )

        key_copy = copy.copy(publicKey)
        key_copy["usage"] = "test_to_fail"

        service_copy = copy.copy(service_key)
        service_copy["routingKeys"] = [key_copy]

        with self.assertRaises(ValueError):
            DIDDoc(
                id="did:sov:LjgpST2rjsoxYegQDRm7EL",
                service=[
                    Service.deserialize(service),
                    Service.deserialize(service_copy),
                ],
                public_key=[VerificationMethod.deserialize(publicKey)],
                authentication=["did:sov:LjgpST2rjsoxYegQDRm7EL#3"],
            )

    async def test_create_did_doc_wrong_id(self):
        with self.assertRaises(ValueError):
            DIDDoc(id="did:sovLjgpST2rjsoxYegQDRm7EL")

    async def test_create_bad(self):
        publicKey2 = copy.copy(publicKey)
        publicKey2["usage"] = "test"

        with self.assertRaises(ValueError):
            DIDDoc(
                id="did:sov:LjgpST2rjsoxYegQDRm7EL",
                service=[Service.deserialize(service)],
                public_key=[VerificationMethod.deserialize(publicKey)],
                authentication=[VerificationMethod.deserialize(publicKey2)],
            )

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

        verification_keys = (
            "verificationMethod",
            "assertionMethod",
            "keyAgreement",
            "capabilityDelegation",
            "capabilityInvocation",
        )
        for key_parm in verification_keys:
            did_doc.add_verification_method(
                type=publicKey["type"],
                controller=publicKey["controller"],
                usage="signing",
                value=publicKey["publicKeyPem"],
                ident="3",
                verification_type=key_parm,
                upsert=True,
            )

        # Not upsert active
        with self.assertRaises(ValueError):
            did_doc.add_verification_method(
                type=publicKey["type"],
                controller=publicKey["controller"],
                value=publicKey["publicKeyPem"],
                ident="3",
            )

        did_doc.id = "did:sov:LjgpST2rjsoxYegQDRm72"
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

        result = DIDDoc.deserialize(json.dumps(result.serialize()))
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
        key_instance = VerificationMethod.deserialize(publicKey)
        did_instance = DIDDoc(
            id=did["id"], public_key=[key_instance], service=[service_instance]
        )
        assert did_instance.id == did["id"]
        assert len(did_instance.service) == 1
        assert did_instance.service[0].serialize() == service
        assert did_instance.service[0] == service_instance

        service2 = copy.copy(service)
        service2["id"] = "did:sov:LjgpST2rjsoxYegQDRm7EL#5"
        key = VerificationMethod.deserialize(publicKey)
        did_instance.add_didcomm_service(
            type="type",
            recipient_keys=key,
            routing_keys=key,
            endpoint="local",
            backward_compatibility=False,
        )
        assert len(did_instance.service) == 2
        # add services with default types: did-communication & IndyAgent
        did_instance.add_didcomm_service(
            recipient_keys=[key], routing_keys=key, endpoint="local"
        )
        assert len(did_instance.service) == 4

    async def test_update_service(self):
        did = {"id": "did:sov:LjgpST2rjsoxYegQDRm7EL", "service": [service]}
        serv_inst = Service.deserialize(service)
        pk_inst = VerificationMethod.deserialize(publicKey)
        did_instance = DIDDoc(id=did["id"], public_key=[pk_inst], service=[serv_inst])
        assert did_instance.id == did["id"]
        assert len(did_instance.service) == 1
        assert did_instance.service[0].serialize() == service
        assert did_instance.service[0] == serv_inst

        did_instance.add_service(
            type="service2",
            endpoint="LjgpST2rjsoxYegQDRm7EL;2",
            ident="2",
            priority=4,
            upsert=True,
        )
        assert len(did_instance.service) == 1
        assert did_instance.service[0].serialize()["type"] == "service2"
        assert did_instance.service[0].serialize()["priority"] == 4
        did_instance.add_service(
            type="service2",
            endpoint="LjgpST2rjsoxYegQDRm7EL;2",
            priority=4,
            upsert=True,
        )
        assert len(did_instance.service) == 2

    async def test_add_new_verification_method(self):
        did = {"id": "did:sov:LjgpST2rjsoxYegQDRm7EL", "publicKey": [publicKey]}
        publicKey_instance = VerificationMethod.deserialize(publicKey)
        did_instance = DIDDoc(id=did["id"], public_key=[publicKey_instance])
        assert did_instance.id == did["id"]
        assert len(did_instance.public_key) == 1
        assert did_instance.public_key[0].serialize() == publicKey
        assert did_instance.public_key[0] == publicKey_instance

        did_instance.add_verification_method(
            type=publicKey["type"], value=publicKey["publicKeyPem"]
        )
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

    async def test_dereference_ok_by_infoID(self):
        did = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "service": [service],
            "publicKey": [publicKey],
            "authentication": [publicKey],
        }

        result = DIDDoc.deserialize(did)

        service_instance = result.dereference(
            DIDUrl("did:sov:LjgpST2rjsoxYegQDRm7EL#2")
        )
        publicKey_instance = result.dereference(
            DIDUrl("did:sov:LjgpST2rjsoxYegQDRm7EL#3")
        )
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
