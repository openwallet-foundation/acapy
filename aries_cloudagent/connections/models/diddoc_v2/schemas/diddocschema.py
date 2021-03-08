"""
DID Document Schema.

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

from marshmallow import (
    Schema,
    fields,
    post_dump,
    post_load,
    pre_load,
    validate,
    INCLUDE,
    ValidationError,
)
from .utils import VERIFICATION_METHOD_KEYS, DID_PATTERN, DID_CONTENT_PATTERN
from .serviceschema import ServiceSchema
from .unionfield import ListOrStringField
from .verificationmethodschema import VerificationMethodSchema, PublicKeyField
import uuid
import copy
import logging

LOGGER = logging.getLogger(__name__)


class DIDDocSchema(Schema):
    """
        Based on https://w3c.github.io/did-core/#did-document-properties spec.

        Example:
    {
       "authentication":[
          {
             "controller":"LjgpST2rjsoxYegQDRm7EL",
             "id":"3",
             "publicKeyPem":"-----BEGIN PUBLIC X...",
             "type":"RsaVerificationKey2018",
             "usage":"signing"
          }
       ],
       "id":"mayor_id",
       "publicKey":[
          {
             "controller":"LjgpST2rjsoxYegQDRm7EL",
             "id":"3",
             "publicKeyPem":"-----BEGIN PUBLIC X...",
             "type":"RsaVerificationKey2018",
             "usage":"signing"
          }
       ],
       "service":[
          {
             "id":"1",
             "priority":1,
             "recipientKeys":[
                "~XXXXXXXXXXXXXXXX",
                "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-1"
             ],
             "routingKeys":[
                "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-4"
             ],
             "serviceEndpoint":"LjgpST2rjsoxYegQDRm7EL;2",
             "type":"one"
          }
       ]
    }
    """

    class Meta:
        """Accept parameter overload."""

        unknown = INCLUDE

    id = fields.Str(required=True, validate=validate.Regexp(DID_PATTERN))
    also_known_as = fields.List(fields.Str(), data_key="alsoKnownAs")
    controller = ListOrStringField()
    verification_method = fields.List(
        fields.Nested(VerificationMethodSchema), data_key="verificationMethod"
    )
    authentication = PublicKeyField()
    assertion_method = PublicKeyField(data_key="assertionMethod")
    key_agreement = PublicKeyField(data_key="keyAgreement")
    capability_invocation = PublicKeyField(data_key="capabilityInvocation")
    capability_delegation = PublicKeyField(data_key="capabilityDelegation")
    public_key = PublicKeyField(data_key="publicKey")
    service = fields.List(fields.Nested(ServiceSchema))

    @pre_load
    def pre_load_did_doc(self, in_data, **kwargs):
        """Preload function."""
        did_doc = copy.deepcopy(in_data)
        verification = did_doc.get("verificationMethod")
        if isinstance(verification, dict):
            did_doc["verificationMethod"] = [verification]
        if did_doc.get("@context"):
            did_doc.pop("@context")

        if not did_doc.get("id"):
            raise ValidationError("ID not found in the DIDDoc")

        did_doc = self._check_verification_method_controller(did_doc)
        did_doc = self._complete_ids(did_doc)
        did_doc = self._refactoring_references(did_doc)

        return did_doc

    @post_load
    def post_load_did_doc(self, data, **kwargs):
        """Post load function."""
        from ..diddoc import DIDDoc

        return DIDDoc(**data)

    @post_dump
    def post_dump_did_doc(self, data, many, **kwargs):
        """Post dump function."""
        for key in tuple(data.keys()):
            if not data.get(key):
                data.pop(key)
        return data

    def _complete_ids(self, in_data):
        for key in in_data:
            value = in_data.get(key)

            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        component_id = item.get("id")
                        if component_id:
                            item["id"] = self._build_id(
                                in_data["id"], component_id, key
                            )
                        else:
                            item["id"] = self._create_id(key, in_data["id"])

        return in_data

    def _create_id(self, key, did_id):
        if key == "service":
            component_id = "service-{}"
        else:
            component_id = "key-{}"

        component_id = component_id.format(uuid.uuid4().hex)
        return self._build_id(did_id, component_id)

    def _check_verification_method_controller(self, in_data):

        for item in VERIFICATION_METHOD_KEYS:

            vm_keys = in_data.get(item, [])
            if isinstance(vm_keys, list):
                for index, key in enumerate(vm_keys):
                    if isinstance(key, dict):
                        if not in_data[item][index].get("controller"):
                            LOGGER.warning(
                                "{} [{}] has no controller, {} setted by default".format(
                                    item, index, in_data["id"]
                                )
                            )
                            in_data[item][index]["controller"] = in_data["id"]

        return in_data

    def _refactoring_references(self, in_data):
        for item in VERIFICATION_METHOD_KEYS:

            vm_keys = in_data.get(item, [])
            if isinstance(vm_keys, list):
                for index, key in enumerate(vm_keys):
                    if isinstance(key, dict):
                        for param in key.keys():
                            if param in VERIFICATION_METHOD_KEYS:
                                reference = key.get(param)

                                reference = self._build_id(in_data["id"], reference)
                                in_data[item][index] = reference
        return in_data

    def _build_id(self, id, reference, key=None):
        result = reference
        if isinstance(reference, list):
            reference = reference[0]
        if id != reference:
            matches = DID_CONTENT_PATTERN.match(reference)
            if not matches:

                if reference[0] != "#":
                    reference = "#{}".format(reference)
                reference = "{}{}".format(id, reference)
                matches = DID_CONTENT_PATTERN.match(reference)

            if matches:
                if result != reference:
                    LOGGER.warning(
                        '"{}" reference changed to "{}"'.format(result, reference)
                    )
                    result = reference

        elif key:
            result = self._create_id(key, reference)

        return result
