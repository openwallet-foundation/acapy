"""VC-API routes web requests schemas."""

from marshmallow import fields, Schema
from ....messaging.models.openapi import OpenAPISchema

from ....messaging.valid import (
    RFC3339_DATETIME_EXAMPLE,
    UUID4_EXAMPLE,
)
from ..validation_result import (
    PresentationVerificationResultSchema,
)
from .options import LDProofVCOptionsSchema
from .credential import (
    CredentialSchema,
    VerifiableCredentialSchema,
)
from .presentation import (
    PresentationSchema,
    VerifiablePresentationSchema,
)


class IssuanceOptionsSchema(Schema):
    """Linked data proof verifiable credential options schema."""

    type = fields.Str(required=False, metadata={"example": "Ed25519Signature2020"})
    created = fields.Str(required=False, metadata={"example": RFC3339_DATETIME_EXAMPLE})
    domain = fields.Str(required=False, metadata={"example": "website.example"})
    challenge = fields.Str(required=False, metadata={"example": UUID4_EXAMPLE})
    # TODO, implement status list publication through a plugin
    # credential_status = fields.Dict(
    #     data_key="credentialStatus",
    #     required=False,
    #     metadata={"example": {"type": "StatusList2021"}},
    # )


class ListCredentialsResponse(OpenAPISchema):
    """Response schema for listing credentials."""

    results = [fields.Nested(VerifiableCredentialSchema)]


class FetchCredentialResponse(OpenAPISchema):
    """Response schema for fetching a credential."""

    results = fields.Nested(VerifiableCredentialSchema)


class IssueCredentialRequest(OpenAPISchema):
    """Request schema for issuing a credential."""

    credential = fields.Nested(CredentialSchema)
    options = fields.Nested(IssuanceOptionsSchema)


class IssueCredentialResponse(OpenAPISchema):
    """Request schema for issuing a credential."""

    verifiableCredential = fields.Nested(VerifiableCredentialSchema)


class VerifyCredentialRequest(OpenAPISchema):
    """Request schema for verifying a credential."""

    verifiableCredential = fields.Nested(VerifiableCredentialSchema)
    options = fields.Nested(LDProofVCOptionsSchema)


class VerifyCredentialResponse(OpenAPISchema):
    """Request schema for verifying an LDP VP."""

    results = fields.Nested(PresentationVerificationResultSchema)


class ProvePresentationRequest(OpenAPISchema):
    """Request schema for proving a presentation."""

    presentation = fields.Nested(PresentationSchema)
    options = fields.Nested(IssuanceOptionsSchema)


class ProvePresentationResponse(OpenAPISchema):
    """Request schema for proving a presentation."""

    verifiablePresentation = fields.Nested(VerifiablePresentationSchema)


class VerifyPresentationRequest(OpenAPISchema):
    """Request schema for verifying a credential."""

    verifiablePresentation = fields.Nested(VerifiablePresentationSchema)
    options = fields.Nested(LDProofVCOptionsSchema)


class VerifyPresentationResponse(OpenAPISchema):
    """Request schema for verifying an LDP VP."""

    results = fields.Nested(PresentationVerificationResultSchema)
