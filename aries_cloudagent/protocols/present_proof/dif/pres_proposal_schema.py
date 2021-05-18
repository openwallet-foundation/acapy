"""DIF Proof Proposal Schema."""
from marshmallow import fields

from ....messaging.models.openapi import OpenAPISchema

from .pres_exch import InputDescriptorsSchema


class DIFProofProposalSchema(OpenAPISchema):
    """Schema for DIF Proposal."""

    input_descriptors = fields.List(
        fields.Nested(
            InputDescriptorsSchema(),
            required=True,
        ),
        required=False,
    )
