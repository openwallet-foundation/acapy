"""VC-API routes requests marshmallow schema classes."""

from marshmallow import fields
from ....messaging.models.openapi import OpenAPISchema

from aries_cloudagent.vc.vc_ld.validation_result import (
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


class ListCredentialResponseSchema(OpenAPISchema):
    """Response schema for listing credentials."""

    credentials = [fields.Nested(VerifiableCredentialSchema)]


class IssueCredentialRequestSchema(OpenAPISchema):
    """Request schema for issuing a credential."""

    credential = fields.Nested(CredentialSchema)
    options = fields.Nested(LDProofVCOptionsSchema)


class IssueCredentialResponseSchema(OpenAPISchema):
    """Request schema for issuing a credential."""

    verifiableCredential = fields.Nested(VerifiableCredentialSchema)


class VerifyCredentialRequestSchema(OpenAPISchema):
    """Request schema for verifying a credential."""

    verifiableCredential = fields.Nested(VerifiableCredentialSchema)
    options = fields.Nested(LDProofVCOptionsSchema)


class VerifyCredentialResponseSchema(PresentationVerificationResultSchema):
    """Request schema for verifying an LDP VP."""


class ProvePresentationRequestSchema(OpenAPISchema):
    """Request schema for proving a presentation."""

    presentation = fields.Nested(PresentationSchema)
    options = fields.Nested(LDProofVCOptionsSchema)


class ProvePresentationResponseSchema(OpenAPISchema):
    """Request schema for proving a presentation."""

    verifiablePresentation = fields.Nested(VerifiablePresentationSchema)


class VerifyPresentationRequestSchema(OpenAPISchema):
    """Request schema for verifying a credential."""

    verifiablePresentation = fields.Nested(VerifiablePresentationSchema)
    options = fields.Nested(LDProofVCOptionsSchema)


class VerifyPresentationResponseSchema(PresentationVerificationResultSchema):
    """Request schema for verifying an LDP VP."""
