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

from ..service import Service


class TestService(AsyncTestCase):
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
        assert result.recipientKeys == test_service["recipientKeys"]
        assert result.routingKeys == test_service["routingKeys"]
        assert result.serviceEndpoint == test_service["serviceEndpoint"]

    def test_deserialize_wrong_id(self):
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

    def test_deserialize_missing_endpoint(self):
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
        test_service = {
            "id": "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-2",
            "type": "one",
            "priority": 1,
            "recipientKeys": ["did:sov:LjgpST2rjsoxYegQDRm7EL#keys-1"],
            "routingKeys": ["did:sov:LjgpST2rjsoxYegQDRm7EL#keys-4"],
            "serviceEndpoint": "LjgpST2rjsoxYegQDRm7EL;2",
        }

        result = Service(
            id=test_service["id"],
            type=test_service["type"],
            priority=test_service["priority"],
            recipientKeys=test_service["recipientKeys"],
            routingKeys=test_service["routingKeys"],
            serviceEndpoint=test_service["serviceEndpoint"],
        )

        assert result.type == test_service["type"]
        assert result.id == test_service["id"]
        assert result.priority == test_service["priority"]
        assert result.recipientKeys == test_service["recipientKeys"]
        assert result.routingKeys == test_service["routingKeys"]
        assert result.serviceEndpoint == test_service["serviceEndpoint"]

        serialized_service = result.serialize()

        assert serialized_service == test_service
