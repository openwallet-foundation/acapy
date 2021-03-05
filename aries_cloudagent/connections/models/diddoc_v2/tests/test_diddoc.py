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
        publicKey_bad_type = copy.copy(publicKey)
        publicKey_bad_type["type"] = ""
        service_key_bad_type = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#8",
            "type": "one",
            "priority": 1,
            "routingKeys": [publicKey_bad_type],
            "serviceEndpoint": "LjgpST2rjsoxYegQDRm7EL;2",
        }
        with self.assertRaises(ValidationError):
            DIDDoc(
                id="did:sov:LjgpST2rjsoxYegQDRm7EL",
                service=[Service.deserialize(service_key_bad_type)],
                public_key=[VerificationMethod.deserialize(publicKey_bad_type)],
            )

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

        did_doc = DIDDoc.deserialize(did)
        assert did_doc.service[0].id
        assert did_doc.service[0].id.find("did:sov:LjgpST2rjsoxYegQDRm7EL") >= 0

    async def test_deserialize_wrong_publicKey(self):
        publicKey2 = copy.copy(publicKey)
        publicKey2.pop("id")

        did = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL",
            "service": [service],
            "publicKey": [publicKey2],
            "authentication": [publicKey],
        }

        did_doc = DIDDoc.deserialize(did)
        assert did_doc.public_key[0].id
        assert did_doc.public_key[0].id.find("did:sov:LjgpST2rjsoxYegQDRm7EL") >= 0

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

    async def test_add_new_service_with_no_existing_keys(self):
        did = {"id": "did:sov:LjgpST2rjsoxYegQDRm7EL", "service": [service]}
        service_instance = Service.deserialize(service)
        key_instance = VerificationMethod.deserialize(publicKey)
        did_instance = DIDDoc(
            id=did["id"], public_key=[key_instance], service=[service_instance]
        )

        service2 = copy.copy(service)
        service2["id"] = "did:sov:LjgpST2rjsoxYegQDRm7EL#5"
        key = VerificationMethod.deserialize(publicKey)

        key.id = "did:sov:LjgpST2rjsoxYegQDRm7EL#999"

        with self.assertRaises(ValueError):
            did_instance.add_didcomm_service(
                type="type",
                recipient_keys=key,
                routing_keys=key,
                endpoint="local",
                backward_compatibility=False,
            )

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

    async def test_add_to_many_verification_method(self):
        did = {"id": "did:sov:LjgpST2rjsoxYegQDRm7EL", "publicKey": [publicKey]}
        publicKey_instance = VerificationMethod.deserialize(publicKey)
        did_instance = DIDDoc(id=did["id"], public_key=[publicKey_instance])
        assert did_instance.id == did["id"]
        assert len(did_instance.public_key) == 1
        assert did_instance.public_key[0].serialize() == publicKey
        assert did_instance.public_key[0] == publicKey_instance

        for item in range(0, 99):
            did_instance.add_verification_method(
                type=publicKey["type"], value=publicKey["publicKeyPem"]
            )

        with self.assertRaises(ValueError):
            did_instance.add_verification_method(
                type=publicKey["type"], value=publicKey["publicKeyPem"]
            )

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

    async def test_universal_resolver(self):
        universal_resolver_DID = {
            "created": "2020-07-14T08:25:15Z",
            "id": "did:ace:0xf81c16a78b257c10fddf87ed4324d433317169a005ddf36a3a1ba937ba9788e3",
            "publicKey": [
                {
                    "controller": "did:ace:0xf81c16a78b257c10fddf87ed4324d433317169a005ddf36a3a1ba937ba9788e3",
                    "publicKeyJwk": '{"kty":"EC","crv":"secp256k1","x":"qdVu4dIjLSS2A_dEp7DYovzoTgFSw309yLTrZanR0Mo","y":"jAhMNEKzvITyyXIr12emFCz5SiCvSwT9qxTRKViKYFk"}',
                    "id": "did:ace:0xf81c16a78b257c10fddf87ed4324d433317169a005ddf36a3a1ba937ba9788e3#selfIssued-1",
                    "type": "EcdsaSecp256k1VerificationKey2019",
                },
                {
                    "controller": "did:ace:0xf81c16a78b257c10fddf87ed4324d433317169a005ddf36a3a1ba937ba9788e3",
                    "publicKeyPem": "-----BEGIN PUBLIC KEY-----\nMIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAmefTYRNzfzrmy7rnyf8WrGg0AnS9McZc\n79xN9W901R4G9U7Ci36N216dhkQS2FiTzYjlcHwDnv8X7lkN1LokfFRR0Q96m11nrvbkmd4lrTsa\nngGHZm+9lLSrjlAbXO+h6lA7aPK0/Vu0HZtdEmXF8RzsxjHhwY6U8hgGGotTjEPL96Zntc5fCB52\nCJMGof+sg5xnu8PxW2/z4Pqkw0n6JWhqg8xVy+vq0FYqtbLOKPHpfSKECG7PnNYqImlnHRQd5r+j\nEtMPFkrT78Unm9lPWIhuVyt1S17hmkJColBNsO+f0G1NE1FE+RALcrZ99Mjc9sb9BYK7L1qk9RW7\n2nLmIBrpu327ZPYQA765bYKLIUq3ItmqR14KlKGHPmlIe6tEE8XrRxT2HYShB19xgLL9tgSkr+wd\nNXmzCSM1GFTMkRh3mOa3BZvqnVgSaJjjeMilPzTDNcbHRqEsj9qbx35Svi02qINBLuXGLQTCitto\nCqfOcxvn37e6QMcLXXkfraOGLhk4RGrjUvvlLN1YmOJdbqeczuIhIdn2ylER4y2ZKYZidjcnUvug\ndF3reduTQscwUV9ZObs13awtjVaAZxnb1DOXu5iKDutqoH+T44JVYAZTYubyyHk2zekO+aTRYMSw\nYKpbqMPbfI9TJ4Nt0RB4QLW/ibBMdH/+FIA10y3TBsUCAwEAAQ==\n-----END PUBLIC KEY-----",
                    "id": "did:ace:0xf81c16a78b257c10fddf87ed4324d433317169a005ddf36a3a1ba937ba9788e3#selfIssued-2",
                    "type": "RsaVerificationKey2018",
                },
                {
                    "controller": "did:ace:0xf81c16a78b257c10fddf87ed4324d433317169a005ddf36a3a1ba937ba9788e3",
                    "publicKeyBase58": "testestetesttest",
                    "id": "did:ace:0xf81c16a78b257c10fddf87ed4324d433317169a005ddf36a3a1ba937ba9788e3#iot-1",
                    "type": "EcdsaSecp256k1VerificationKey2019",
                },
                {
                    "controller": "did:ace:0xf81c16a78b257c10fddf87ed4324d433317169a005ddf36a3a1ba937ba9788e3",
                    "publicKeyHex": "1920ABC829283",
                    "id": "did:ace:0xf81c16a78b257c10fddf87ed4324d433317169a005ddf36a3a1ba937ba9788e3#selfIssued-3",
                    "type": "EcdsaSecp256r1VerificationKey2019",
                },
                {
                    "publicKeyBase64": "1AJEOSLE920ABC829283",
                    "type": "EcdsaSecp256r1VerificationKey2019",
                },
            ],
            "proof": {
                "creator": "did:ace:0xf81c16a78b257c10fddf87ed4324d433317169a005ddf36a3a1ba937ba9788e3#selfIssued-1",
                "created": "2020-07-14T08:25:16Z",
                "type": "LinkedDataSignature2015",
                "signatureValue": "MEQCIDiWhWaHte+/G/9emToSx6JwYG7OWEGCm5u1P1QXUfs2AiAQzp+gO1nLaEMKHQ22bxxT9T9pnm0bIfYHbqeAHsKXxA==",
            },
            "@context": "https://www.w3.org/ns/did/v1",
            "updated": "2020-07-14T08:25:15Z",
        }

        result = DIDDoc.deserialize(universal_resolver_DID)
        assert len(result.public_key) == 5
        assert result.public_key[4].id
        assert result.public_key[4].controller

        # Dependencies of other Verification Methods
        universal_resolver_DID_2 = {
            "@context": ["https://www.w3.org/ns/did/v1"],
            "id": "did:btcr:xz35-jznz-q9yu-ply",
            "verificationMethod": [
                {
                    "type": ["EcdsaSecp256k1VerificationKey2019"],
                    "id": ["did:btcr:xz35-jznz-q9yu-ply#key-0"],
                    "publicKeyBase58": "020a5a5c8c3575489cd2c17d43f642fc2b34792d47c9b026fafe33b3469e31b841",
                },
                {
                    "type": ["EcdsaSecp256k1VerificationKey2019"],
                    "id": "did:btcr:xz35-jznz-q9yu-ply#key-1",
                    "publicKeyBase58": "020a5a5c8c3575489cd2c17d43f642fc2b34792d47c9b026fafe33b3469e31b841",
                },
                {
                    "type": ["EcdsaSecp256k1VerificationKey2019"],
                    "id": "did:btcr:xz35-jznz-q9yu-ply#satoshi",
                    "publicKeyBase58": "020a5a5c8c3575489cd2c17d43f642fc2b34792d47c9b026fafe33b3469e31b841",
                },
            ],
            "authentication": [
                {
                    "type": ["EcdsaSecp256k1SignatureAuthentication2019"],
                    "verificationMethod": "#satoshi",
                }
            ],
        }
        result2 = DIDDoc.deserialize(universal_resolver_DID_2)
        assert (
            result2.authentication[0].serialize()
            == result2.verification_method[2].serialize()
        )

        # No existing service ID
        universal_resolver_DID_3 = {
            "@context": "https://www.w3.org/2019/did/v1",
            "id": "did:stack:v0:16EMaNw3pkn3v6f2BgnSSs53zAKH4Q8YJg-0",
            "service": [
                {"type": "blockstack", "serviceEndpoint": "https://core.blockstack.org"}
            ],
            "publicKey": [
                {
                    "id": "did:stack:v0:16EMaNw3pkn3v6f2BgnSSs53zAKH4Q8YJg-0",
                    "type": "Secp256k1VerificationKey2018",
                    "publicKeyHex": "040fadbbcea0ff3b05f03195b41cd991d7a0af8bd38559943aec99cbdaf0b22cc806b9a4f07579934774cc0c155e781d45c989f94336765e88a66d91cfb9f060b0",
                }
            ],
        }

        result3 = DIDDoc.deserialize(universal_resolver_DID_3)
        assert result3.service[0].id

    async def test_universal_resolver_wrong(self):

        universal_resolver_DID_error = {
            "@context": ["https://www.w3.org/ns/did/v1"],
            "id": "did:btcr:xz35-jznz-q9yu-ply",
            "verificationMethod": {
                "type": ["EcdsaSecp256k1VerificationKey2019"],
                "id": ["did:btcr:xz35-jznz-q9yu-ply#key-0"],
                "publicKeyBase99": "020a5a5c8c3575489cd2c17d43f642fc2b34792d47c9b026fafe33b3469e31b841",
            },
        }
        with self.assertRaises(ValidationError):
            DIDDoc.deserialize(universal_resolver_DID_error)
