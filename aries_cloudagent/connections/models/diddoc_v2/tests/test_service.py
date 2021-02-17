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
from marshmallow.exceptions import ValidationError

from aries_cloudagent.connections.models.diddoc_v2 import (
    Service,
    VerificationMethod,
    PublicKeyType,
)


class TestService(AsyncTestCase):
    async def test_create_update_service(self):
        verification = VerificationMethod(
            id="did:sov:LjgpST2rjsoxYegQDRm7EL#555",
            type=PublicKeyType.ED25519_SIG_2018,
            controller="did:sov:LjgpST2rjsoxYegQDRm7EL#555",
            value="ZXd1ZXduZXduaXV3ZWg3d2V3ZW5q",
        )
        service = Service(
            id="did:sov:LjgpST2rjsoxYegQDRm7EL#1",
            type="type_one",
            service_endpoint="LjgpST2rjsoxYegQDRm7EL",
        )

        assert service.id == "did:sov:LjgpST2rjsoxYegQDRm7EL#1"
        assert service.type == "type_one"
        assert service.service_endpoint == "LjgpST2rjsoxYegQDRm7EL"

        service.id = "did:sov:LjgpST2rjsoxYegQDRm7EL#2"
        service.type = "type_two"
        service.service_endpoint = "localhost"
        service.priority = 1
        service.recipient_keys = verification
        service.routing_keys = [verification]

        assert service.id == "did:sov:LjgpST2rjsoxYegQDRm7EL#2"
        assert service.type == "type_two"
        assert service.service_endpoint == "localhost"
        assert service.priority == 1
        assert service.recipient_keys == verification
        assert service.routing_keys == [verification]

    async def test_deserialize_ok(self):
        test_service = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-2",
            "type": "one",
            "priority": 1,
            "recipientKeys": ["did:sov:LjgpST2rjsoxYegQDRm7EL#keys-1"],
            "routingKeys": ["did:sov:LjgpST2rjsoxYegQDRm7EL#keys-4"],
            "serviceEndpoint": "LjgpST2rjsoxYegQDRm7EL;2",
        }
        result = Service.deserialize(test_service)
        assert result.type == test_service["type"]
        assert result.id == test_service["id"]
        assert result.priority == test_service["priority"]
        assert result.recipient_keys == test_service["recipientKeys"]
        assert result.routing_keys == test_service["routingKeys"]
        assert result.service_endpoint == test_service["serviceEndpoint"]

    async def test_deserialize_fail(self):
        test_service = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-2",
            "type": "one",
            "priority": 1,
            "recipientKeys": True,
            "routingKeys": "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-4",
            "serviceEndpoint": "LjgpST2rjsoxYegQDRm7EL;2",
        }
        with self.assertRaises(ValidationError):
            Service.deserialize(test_service)
        test_service["type"] = False
        with self.assertRaises(ValidationError):
            Service.deserialize(test_service)
        test_service["type"] = "one"
        test_service["serviceEndpoint"] = False
        with self.assertRaises(ValidationError):
            Service.deserialize(test_service)

    async def test_deserialize_wrong_id(self):
        test_service = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL##keys-2",
            "type": "one",
            "priority": 1,
            "recipientKeys": ["did:sov:LjgpST2rjsoxYegQDRm7EL#keys-1"],
            "routingKeys": ["did:sov:LjgpST2rjsoxYegQDRm7EL#keys-4"],
            "serviceEndpoint": "LjgpST2rjsoxYegQDRm7EL;2",
        }

        with self.assertRaises(ValidationError):
            Service.deserialize(test_service)

    async def test_deserialize_missing_endpoint(self):
        test_service = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-2",
            "type": "one",
            "priority": 1,
            "recipientKeys": ["did:sov:LjgpST2rjsoxYegQDRm7EL#keys-1"],
            "routingKeys": ["did:sov:LjgpST2rjsoxYegQDRm7EL#keys-4"],
        }

        with self.assertRaises(ValidationError):
            Service.deserialize(test_service)

    async def test_serialize_ok(self):
        verification = VerificationMethod(
            id="did:sov:LjgpST2rjsoxYegQDRm7EL#555",
            type=PublicKeyType.ED25519_SIG_2018,
            controller="did:sov:LjgpST2rjsoxYegQDRm7EL#555",
            value="ZXd1ZXduZXduaXV3ZWg3d2V3ZW5q",
        )

        test_service = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-2",
            "type": "one",
            "priority": 1,
            "recipientKeys": "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-4",
            "routingKeys": [verification],
            "serviceEndpoint": "LjgpST2rjsoxYegQDRm7EL;2",
        }

        result = Service(
            id=test_service["id"],
            type=test_service["type"],
            priority=test_service["priority"],
            recipient_keys=test_service["recipientKeys"],
            routing_keys=test_service["routingKeys"],
            service_endpoint=test_service["serviceEndpoint"],
        )

        assert result.type == test_service["type"]
        assert result.id == test_service["id"]
        assert result.priority == test_service["priority"]
        assert result.recipient_keys == test_service["recipientKeys"]
        assert result.routing_keys == test_service["routingKeys"]
        assert result.service_endpoint == test_service["serviceEndpoint"]

        serialized_service = result.serialize()

        assert serialized_service == test_service
