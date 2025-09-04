"""AnonCreds tails file models."""

from marshmallow import fields

from .....messaging.models.openapi import OpenAPISchema
from .....messaging.valid import (
    ANONCREDS_REV_REG_ID_EXAMPLE,
    ANONCREDS_REV_REG_ID_VALIDATE,
)


class AnonCredsRevRegIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking rev reg id."""

    rev_reg_id = fields.Str(
        required=True,
        validate=ANONCREDS_REV_REG_ID_VALIDATE,
        metadata={
            "description": "Revocation Registry identifier",
            "example": ANONCREDS_REV_REG_ID_EXAMPLE,
        },
    )
