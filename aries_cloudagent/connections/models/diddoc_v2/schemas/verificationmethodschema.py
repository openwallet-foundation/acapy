"""
DID Document verification method schema.

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

import re

from marshmallow import Schema, fields, post_load, validate, ValidationError

from .....resolver.did import DID_PATTERN
from .unionfield import ListOrStringField

DID_PATTERN = re.compile("{}#[a-zA-Z0-9._-]+".format(DID_PATTERN.pattern))


class VerificationMethodSchema(Schema):
    """
    Based on https://w3c.github.io/did-core/#verification-method-properties spec.

    Example:

    {"id": "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-4",
     "type": "RsaVerificationKey2018",
     "controller": "did:sov:LjgpST2rjsoxYegQDRm7EL",
     "publicKeyPem": "-----BEGIN PUBLIC X...",
     "publicKeyBase58",
     "publicKeyHex": "0361f286ada2a6b2c74bc6ed44a71ef59fb9dd15eca9283cbe5608aeb516730f33",
     "publicKeyJwk": {
        "kty": "EC",
        "crv": "secp256k1",
        "kid": "JUvpllMEYUZ2joO59UNui_XYDqxVqiFLLAJ8klWuPBw",
        "x": "dWCvM4fTdeM0KmloF57zxtBPXTOythHPMm1HCLrdd3A",
        "y": "36uMVGM7hnw-N6GnjFcihWE3SkrhMLzzLCdPMXPEXlA"},

      }
    """

    id = fields.Str(required=True, validate=validate.Regexp(DID_PATTERN))
    type = fields.Str(required=True)
    controller = ListOrStringField(required=True)
    publicKeyHex = fields.Str()
    publicKeyPem = fields.Str()
    publicKeyJwk = fields.Dict()
    publicKeyBase58 = fields.Str()

    @post_load
    def make_public_key(self, data, **_kwargs):
        """Create public key on load from schema."""
        from ..verification_method import VerificationMethod

        return VerificationMethod(**data)


class PublicKeyField(fields.Field):
    """Public Key field for Marshmallow."""

    def _serialize(self, value, attr, obj, **kwargs):
        if isinstance(value, list):
            for idx, val in enumerate(value):
                if not isinstance(val, str):
                    value[idx] = val.serialize()
            return value
        else:
            return "".join(str(d) for d in value)

    def _deserialize(self, value, attr, data, **kwargs):
        from aries_cloudagent.connections.models.diddoc_v2 import VerificationMethod

        if isinstance(value, str):
            return value
        elif isinstance(value, list):
            for idx, val in enumerate(value):
                if isinstance(val, dict):
                    if (
                        (not val.get("id"))
                        or (not val.get("type"))
                        or (not val.get("controller"))
                    ):
                        raise ValidationError(
                            "VerificationMethod Map must have id, type & controler"
                        )
                    value[idx] = VerificationMethod(**val)
            return value
        else:
            raise ValidationError("Field should be str, list or dict")
