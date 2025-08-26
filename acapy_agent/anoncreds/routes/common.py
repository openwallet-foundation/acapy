"""Common definitions for AnonCreds routes."""

from marshmallow import fields

from ...messaging.models.openapi import OpenAPISchema
from ...messaging.valid import UUIDFour

endorser_connection_id_description = (
    "Connection identifier (optional) (this is an example). "
    "You can set this if you know the endorser's connection id you want to use. "
    "If not specified then the agent will attempt to find an endorser connection."
)
create_transaction_for_endorser_description = (
    "Create transaction for endorser (optional, default false). "
    "Use this for agents who don't specify an author role but want to "
    "create a transaction for an endorser to sign."
)


class EndorserOptionsSchema(OpenAPISchema):
    """Common schema for endorser-related options."""

    endorser_connection_id = fields.Str(
        metadata={
            "description": endorser_connection_id_description,
            "example": UUIDFour.EXAMPLE,
        },
        required=False,
    )

    create_transaction_for_endorser = fields.Bool(
        metadata={
            "description": create_transaction_for_endorser_description,
            "example": False,
        },
        required=False,
    )


class SchemaQueryFieldsMixin(OpenAPISchema):
    """Mixin for common schema query fields."""

    schema_name = fields.Str(
        metadata={
            "description": "Schema name",
            "example": "example-schema",
        }
    )
    schema_version = fields.Str(
        metadata={
            "description": "Schema version",
            "example": "1.0",
        }
    )
