"""DID routes web requests schemas."""

from marshmallow import fields
from ..messaging.models.openapi import OpenAPISchema


class DIDKeyRegistrationRequest(OpenAPISchema):
    """Request schema for registering key dids."""

    key_type = fields.Str(
        default="ed25519",
        required=False,
        metadata={
            "description": "Key Type",
            "example": "ed25519",
        },
    )


class DIDKeyRegistrationResponse(OpenAPISchema):
    """Response schema for registering web dids."""

    did_document = fields.Dict()
