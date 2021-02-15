"""openapi schemas."""
from ...messaging.models.openapi import OpenAPISchema
from marshmallow import Schema, fields, validate
from marshmallow.validate import Regexp

# https://tools.ietf.org/html/rfc3986#appendix-B
uri_validate = Regexp(r"^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?")
# RFC3339 datetime regex taken from https://stackoverflow.com/a/24544212
datetime_validate = Regexp(
    rf"^\\d{4}-\\d{2}-\\d{2}T\\d{2}%3A\\d{2}%3A\\"
    rf"d{2}(?:%2E\\d+)?[A-Z]?(?:[+.-](?:08%3A\\d{2}|\\d{2}[A-Z]))?$"
)


class SignRequestSchema(OpenAPISchema):
    """Request schema for signing a jsonld doc."""

    verkey = fields.Str(required=True, description="verkey to use for signing")
    doc_schema = Schema.from_dict(
        {
            "credential": fields.Dict(required=False),
            "options": fields.Dict(required=False),
        }
    )
    doc = fields.Nested(doc_schema(), required=True, description="JSON-LD Doc to sign")


class SignResponseSchema(OpenAPISchema):
    """Response schema for a signed jsonld doc."""

    signed_doc = fields.Dict(required=True)


class VerifyRequestSchema(OpenAPISchema):
    """Request schema for signing a jsonld doc."""

    verkey = fields.Str(
        required=False, description="verkey to use for doc verification"
    )
    doc = fields.Dict(required=True, description="JSON-LD Doc to verify")


class VerifyResponseSchema(OpenAPISchema):
    """Response schema for verification result."""

    valid = fields.Bool(required=True)


class TenBasicDocumentSchema(OpenAPISchema):
    """W3C Document schema for validation."""

    _at_context = (
        fields.List(
            fields.Str(),  # do not support key value structure in context
            data_key="@context",
            allow_none=False,
            validate=validate.Predicate(
                lambda context: context[0] == "https://www.w3.org/2018/credentials/v1",
                error="first value MUST be https://www.w3.org/2018/credentials/v1",
            ),
        ),
    )
    _id = fields.Str(validate=uri_validate, data_key="id")
    _type = fields.List(
        fields.Str(),
        data_key="type",
        allow_none=False,
        validate=validate.Predicate(
            lambda types: "VerifiableCredential" in types,
            error="VerifiableCredential must be a type",
        ),
    )
    _subject = fields.Str(
        required=True,
        data_key="credentialSubject",
        validate=uri_validate,
    )
    _issuer = fields.Str(required=True, data_key="issuer", validate=uri_validate)
    _issuance_date = fields.Str(
        required=True, data_key="issuanceDate", validate=datetime_validate
    )
    _expirationDate = fields.Str(
        required=False, data_key="expirationDate", validate=datetime_validate
    )
    _Presentations = Schema.from_dict(
        {
            "VerifiablePresentation": fields.Str(required=True),
            "verifiableCredential": fields.Str(required=True),
        }
    )
    proof = Schema.from_dict(
            {
                "type": fields.Str(required=True),
                "created": fields.Str(required=True),
                "verificationMethod": fields.Str(required=True),
                "proofPurpose": fields.Str(required=True),
                "jws": fields.Str(required=True),
            },
    )
