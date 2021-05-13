"""DIF Proof Request Schema."""
from marshmallow import fields

from ....messaging.models.openapi import OpenAPISchema

from .pres_exch import PresentationDefinitionSchema, DIFOptionsSchema


class DIFPresRequestSchema(OpenAPISchema):
    """Schema for DIF Proof request."""

    options = fields.Nested(
        DIFOptionsSchema(),
        required=False,
    )
    presentation_definition = fields.Nested(
        PresentationDefinitionSchema(),
        required=True,
    )
