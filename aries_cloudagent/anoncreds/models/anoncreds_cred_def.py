"""Anoncreds cred def OpenAPI validators"""
from marshmallow import Schema, fields

from aries_cloudagent.messaging.valid import NUM_STR_WHOLE

from ...messaging.models.openapi import OpenAPISchema


class PrimarySchema(OpenAPISchema):
    """Parameters and validators for credential definition primary."""

    n = fields.Str(**NUM_STR_WHOLE)
    s = fields.Str(**NUM_STR_WHOLE)
    r = fields.Nested(
        Schema.from_dict(
            {
                "master_secret": fields.Str(**NUM_STR_WHOLE),
                "number": fields.Str(**NUM_STR_WHOLE),
                "remainder": fields.Str(**NUM_STR_WHOLE),
            }
        ),
        name="CredDefValuePrimaryRSchema",
    )
    rctxt = fields.Str(**NUM_STR_WHOLE)
    z = fields.Str(**NUM_STR_WHOLE)


class CredDefValueSchema(OpenAPISchema):
    """Parameters and validators for credential definition value."""

    primary = fields.Nested(PrimarySchema())
