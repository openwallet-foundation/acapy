"""Admin routes for presentations."""

from marshmallow import fields

from ....utils.tracing import AdminAPIMessageTracingSchema

from ..indy.requested_creds import (
    IndyRequestedCredsRequestedAttrSchema,
    IndyRequestedCredsRequestedPredSchema,
)


class IndyPresSpecSchema(AdminAPIMessageTracingSchema):
    """Request schema for indy proof specification to send as presentation."""

    self_attested_attributes = fields.Dict(
        description="Self-attested attributes to build into proof",
        required=True,
        keys=fields.Str(example="attr_name"),  # marshmallow/apispec v3.0 ignores
        values=fields.Str(
            example="self_attested_value",
            description=(
                "Self-attested attribute values to use in requested-credentials "
                "structure for proof construction"
            ),
        ),
    )
    requested_attributes = fields.Dict(
        description=(
            "Nested object mapping proof request attribute referents to "
            "requested-attribute specifiers"
        ),
        required=True,
        keys=fields.Str(example="attr_referent"),  # marshmallow/apispec v3.0 ignores
        values=fields.Nested(IndyRequestedCredsRequestedAttrSchema()),
    )
    requested_predicates = fields.Dict(
        description=(
            "Nested object mapping proof request predicate referents to "
            "requested-predicate specifiers"
        ),
        required=True,
        keys=fields.Str(example="pred_referent"),  # marshmallow/apispec v3.0 ignores
        values=fields.Nested(IndyRequestedCredsRequestedPredSchema()),
    )
    trace = fields.Bool(
        description="Whether to trace event (default false)",
        required=False,
        example=False,
    )
