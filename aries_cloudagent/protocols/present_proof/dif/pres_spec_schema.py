"""DIF Proof Request Schema."""
from marshmallow import fields

from ....messaging.models.openapi import OpenAPISchema

from .pres_exch import PresentationDefinitionSchema


class DIFPresSpecSpecSchema(OpenAPISchema):
    """Schema for DIF Presentation Spec schema."""

    issuer_id = fields.Str(
        description=(
            (
                "Issuer identifier to sign the presentation,"
                " if different from current public DID"
            )
        ),
        required=False,
    )
    presentation_definition = fields.Nested(
        PresentationDefinitionSchema(),
        required=False,
    )
