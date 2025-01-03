"""VC-API routes web requests schemas."""

from marshmallow import fields

from ....messaging.models.openapi import OpenAPISchema
from ..validation_result import PresentationVerificationResultSchema
from .credential import CredentialSchema, VerifiableCredentialSchema
from .options import LDProofVCOptionsSchema
from .presentation import PresentationSchema, VerifiablePresentationSchema


class ListCredentialsResponse(OpenAPISchema):
    """Response schema for listing credentials."""

    results = fields.List(fields.Nested(VerifiableCredentialSchema))


class FetchCredentialResponse(OpenAPISchema):
    """Response schema for fetching a credential."""

    results = fields.Nested(VerifiableCredentialSchema)


class IssueCredentialRequest(OpenAPISchema):
    """Request schema for issuing a credential."""

    credential = fields.Nested(CredentialSchema)
    options = fields.Nested(LDProofVCOptionsSchema)


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


class StoreCredentialRequest(OpenAPISchema):
    """Request schema for verifying an LDP VP."""

    verifiableCredential = fields.Nested(VerifiableCredentialSchema)


class StoreCredentialResponse(OpenAPISchema):
    """Request schema for verifying an LDP VP."""

    credentialId = fields.Str()


class ProvePresentationRequest(OpenAPISchema):
    """Request schema for proving a presentation."""

    presentation = fields.Nested(PresentationSchema)
    options = fields.Nested(LDProofVCOptionsSchema)


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
