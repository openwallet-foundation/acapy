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

from marshmallow import Schema, fields, post_load, pre_load, post_dump, validate
from .verificationmethodschema import VerificationMethodSchema
from .serviceschema import ServiceSchema
from .unionfield import ListOrStringField, PublicKeyField
from ...resolver.did import DID_PATTERN
import re


class DIDDocSchema(Schema):
    """
        Based on https://w3c.github.io/did-core/#did-document-properties

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

    id = fields.Str(required=True, validate=validate.Regexp(DID_PATTERN))
    alsoKnownAs = fields.List(fields.Str())
    controller = ListOrStringField()
    verificationMethod = fields.List(fields.Nested(VerificationMethodSchema))
    authentication = PublicKeyField()
    assertionMethod = PublicKeyField()
    keyAgreement = PublicKeyField()
    capabilityInvocation = PublicKeyField()
    capabilityDelegation = PublicKeyField()
    publicKey = PublicKeyField()
    service = fields.List(fields.Nested(ServiceSchema))

    @pre_load
    def pre_load_did_doc(self, in_data, **kwargs):
        verification = in_data.get("verificationMethod")
        if isinstance(verification, dict):
            in_data["verificationMethod"] = [verification]
        if in_data.get("@context"):
            in_data.pop("@context")
        return in_data

    @post_load
    def post_load_did_doc(self, data, **kwargs):
        from ..diddoc import DIDDoc

        return DIDDoc(**data)

    @post_dump
    def post_dump_did_doc(self, data, many, **kwargs):
        for key in tuple(data.keys()):
            if not data.get(key):
                data.pop(key)
        return data
