"""AnonCreds schema models."""

from marshmallow import fields

from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import (
    ANONCREDS_DID_EXAMPLE,
    ANONCREDS_SCHEMA_ID_EXAMPLE,
)
from ...models.schema import AnonCredsSchemaSchema
from ..common.schemas import EndorserOptionsSchema, SchemaQueryFieldsMixin


class SchemaIdMatchInfo(OpenAPISchema):
    """Path parameters and validators for request taking schema id."""

    schema_id = fields.Str(
        metadata={
            "description": "Schema identifier",
            "example": ANONCREDS_SCHEMA_ID_EXAMPLE,
        }
    )


class SchemaPostOptionSchema(EndorserOptionsSchema):
    """Parameters and validators for schema options."""

    pass


class SchemasQueryStringSchema(SchemaQueryFieldsMixin):
    """Parameters and validators for query string in schemas list query."""

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
