from marshmallow import fields

from ....messaging.models.base import Schema
from ....messaging.valid import (
    CREDENTIAL_CONTEXT,
    CREDENTIAL_TYPE,
    CREDENTIAL_SUBJECT,
    URI,
)


class LDCredential(Schema):
    # MTODO: Support union types
    context = fields.List(
        fields.Str(),
        data_key="@context",
        required=True,
        description="The JSON-LD context of the credential",
        **CREDENTIAL_CONTEXT,
    )
    id = fields.Str(
        required=False,
        desscription="The ID of the credential",
        example="http://example.edu/credentials/1872",
        validate=URI(),
    )
    type = fields.List(
        fields.Str(),
        required=True,
        description="The JSON-LD type of the credential",
        **CREDENTIAL_TYPE,
    )
    issuer = fields.Str(
        required=False, description="The JSON-LD Verifiable Credential Issuer"
    )
    issuance_date = fields.DateTime(
        data_key="issuanceDate",
        required=False,
        description="The issuance date",
        example="2010-01-01T19:73:24Z",
    )
    expiration_date = fields.DateTime(
        data_key="expirationDate",
        required=False,
        description="The expiration date",
        example="2010-01-01T19:73:24Z",
    )
    credential_subject = fields.Dict(
        required=True,
        keys=fields.Str(),
        data_key="credentialSubject",
        **CREDENTIAL_SUBJECT,
    )
    # TODO: add typing
    credential_schema = fields.Dict(required=False, data_key="credentialSchema")


class LDVerifiableCredential(LDCredential):
    # TODO: support union types, better dict key typing
    # Add proof schema
    proof = fields.Dict(
        required=True,
        keys=fields.Str(),
    )
