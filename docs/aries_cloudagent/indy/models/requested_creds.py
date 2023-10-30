"""Admin routes for presentations."""

from marshmallow import fields

from ...messaging.models.openapi import OpenAPISchema
from ...messaging.valid import INT_EPOCH_EXAMPLE, INT_EPOCH_VALIDATE


class IndyRequestedCredsRequestedAttrSchema(OpenAPISchema):
    """Schema for requested attributes within indy requested credentials structure."""

    cred_id = fields.Str(
        required=True,
        metadata={
            "example": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "description": (
                "Wallet credential identifier (typically but not necessarily a UUID)"
            ),
        },
    )
    revealed = fields.Bool(
        dump_default=True,
        metadata={"description": "Whether to reveal attribute in proof (default true)"},
    )


class IndyRequestedCredsRequestedPredSchema(OpenAPISchema):
    """Schema for requested predicates within indy requested credentials structure."""

    cred_id = fields.Str(
        required=True,
        metadata={
            "description": (
                "Wallet credential identifier (typically but not necessarily a UUID)"
            ),
            "example": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        },
    )
    timestamp = fields.Int(
        required=False,
        validate=INT_EPOCH_VALIDATE,
        metadata={
            "description": "Epoch timestamp of interest for non-revocation proof",
            "strict": True,
            "example": INT_EPOCH_EXAMPLE,
        },
    )
