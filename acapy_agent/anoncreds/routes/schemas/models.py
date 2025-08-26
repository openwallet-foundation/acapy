"""AnonCreds schema models."""

from marshmallow import fields

from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import (
    ANONCREDS_DID_EXAMPLE,
    ANONCREDS_SCHEMA_ID_EXAMPLE,
    UUIDFour,
)
from ...models.schema import AnonCredsSchemaSchema
from ..common import (
    create_transaction_for_endorser_description,
    endorser_connection_id_description,
)


class SchemaIdMatchInfo(OpenAPISchema):
    """Path parameters and validators for request taking schema id."""

    schema_id = fields.Str(
        metadata={
            "description": "Schema identifier",
            "example": ANONCREDS_SCHEMA_ID_EXAMPLE,
        }
    )


class SchemaPostOptionSchema(OpenAPISchema):
    """Parameters and validators for schema options."""

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


class SchemasQueryStringSchema(OpenAPISchema):
    """Parameters and validators for query string in schemas list query."""

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
    schema_issuer_id = fields.Str(
        metadata={
            "description": "Schema issuer identifier",
            "example": ANONCREDS_DID_EXAMPLE,
        }
    )


class GetSchemasResponseSchema(OpenAPISchema):
    """Parameters and validators for schema list all response."""

    schema_ids = fields.List(
        fields.Str(
            metadata={
                "description": "Schema identifiers",
                "example": ANONCREDS_SCHEMA_ID_EXAMPLE,
            }
        )
    )


class SchemaPostRequestSchema(OpenAPISchema):
    """Parameters and validators for query string in create schema."""

    schema = fields.Nested(AnonCredsSchemaSchema())
    options = fields.Nested(SchemaPostOptionSchema())
