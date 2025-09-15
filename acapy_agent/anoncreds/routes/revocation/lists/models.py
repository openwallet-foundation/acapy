"""AnonCreds revocation lists models."""

from marshmallow import fields

from .....messaging.models.openapi import OpenAPISchema
from .....messaging.valid import ANONCREDS_REV_REG_ID_EXAMPLE
from ...common.schemas import EndorserOptionsSchema


class RevListOptionsSchema(EndorserOptionsSchema):
    """Parameters and validators for revocation list options."""

    pass


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
