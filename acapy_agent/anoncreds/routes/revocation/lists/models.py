"""AnonCreds revocation lists models."""

from marshmallow import fields

from .....messaging.models.openapi import OpenAPISchema
from .....messaging.valid import ANONCREDS_REV_REG_ID_EXAMPLE
from ...common import (
    create_transaction_for_endorser_description,
    endorser_connection_id_description,
)


class RevListOptionsSchema(OpenAPISchema):
    """Parameters and validators for revocation list options."""

    endorser_connection_id = fields.Str(
        metadata={
            "description": endorser_connection_id_description,
            "example": "UUIDFour.EXAMPLE",
        },
        required=False,
    )
    create_transaction_for_endorser = fields.Bool(
        metadata={
            "description": create_transaction_for_endorser_description,
            "example": False,
        },
        required=False,
    )


class RevListCreateRequestSchema(OpenAPISchema):
    """Request schema for revocation registry creation request."""

    rev_reg_def_id = fields.Str(
        metadata={
            "description": "Revocation registry definition identifier",
            "example": ANONCREDS_REV_REG_ID_EXAMPLE,
        },
        required=True,
    )
    options = fields.Nested(RevListOptionsSchema())
