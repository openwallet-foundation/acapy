"""Options for specifying how the linked data proof is created."""

from marshmallow import Schema, fields

from ...messaging.valid import (
    RFC3339_DATETIME_EXAMPLE,
)


class OptionsSchema(Schema):
    """Linked data proof verifiable credential options schema."""

    created = fields.Str(
        data_key="created",
        required=False,
        metadata={
            "example": RFC3339_DATETIME_EXAMPLE,
        },
    )
    type = fields.Str(
        data_key="type",
        required=False,
        metadata={
            "example": "Ed25519Signature2020",
        },
    )
    domain = fields.Str(
        data_key="domain",
        required=False,
        metadata={
            "example": "website.example",
        },
    )
    challenge = fields.Str(
        data_key="challenge",
        required=False,
        metadata={
            "example": "6e62f66e-67de-11eb-b490-ef3eeefa55f2",
        },
    )
    # TODO enable credentialStatusList publication
    # credentialStatus  = fields.Dict(data_key="credentialStatus", required=False,
    #     metadata={
    #         "example": {"type": "BitstringStatusList"},
    #     })
