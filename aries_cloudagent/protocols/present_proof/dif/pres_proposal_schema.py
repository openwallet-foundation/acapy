"""DIF Proof Proposal Schema."""
from marshmallow import fields

from ....messaging.models.openapi import OpenAPISchema

from .pres_exch import InputDescriptorsSchema


class DIFPresProposalSchema(OpenAPISchema):
    """Schema for DIF Proposal."""

    input_descriptors = fields.List(
        fields.Nested(
            InputDescriptorsSchema(),
            required=True,
        ),
        data_key="input_descriptors",
        required=False,
    )
