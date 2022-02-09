"""DIF Proof Request Schema."""
from marshmallow import fields

from ....messaging.models.openapi import OpenAPISchema

from .pres_exch import PresentationDefinitionSchema, DIFOptionsSchema


class DIFProofRequestSchema(OpenAPISchema):
    """Schema for DIF Proof request."""

    options = fields.Nested(
        DIFOptionsSchema(),
        required=False,
    )
    presentation_definition = fields.Nested(
        PresentationDefinitionSchema(),
        required=True,
    )


class DIFPresSpecSchema(OpenAPISchema):
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
    record_ids = fields.Dict(
        description=(
            (
                "Mapping of input_descriptor id to list "
                "of stored W3C credential record_id"
            )
        ),
        example=(
            {
                "<input descriptor id_1>": ["<record id_1>", "<record id_2>"],
                "<input descriptor id_2>": ["<record id>"],
            }
        ),
        required=False,
    )
    presentation_definition = fields.Nested(
        PresentationDefinitionSchema(),
        required=False,
    )
