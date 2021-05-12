"""DIF Proof Request Schema."""
from marshmallow import fields

from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import UUID4

from .pres_exch import PresentationDefinitionSchema


class DIFPresRequestSchema(OpenAPISchema):
    """Schema for DIF Proof request."""

    challenge = fields.String(
        description="Challenge protect against replay attack",
        required=False,
        **UUID4,
    )
    domain = fields.String(
        description="Domain protect against replay attack",
        required=False,
        example="4jt78h47fh47",
    )
    presentation_definition = fields.Nested(
        PresentationDefinitionSchema(),
        required=True,
    )
