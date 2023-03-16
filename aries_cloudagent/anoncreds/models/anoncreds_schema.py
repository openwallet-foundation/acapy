"""Anoncreds Schema OpenAPI validators"""

from typing import Any, Dict, List

from marshmallow import EXCLUDE, fields

from aries_cloudagent.anoncreds.models.anoncreds_valid import (
    ANONCREDS_SCHEMA_ID,
    ANONCREDS_VERSION,
)
from aries_cloudagent.messaging.models.base import BaseModel, BaseModelSchema

from ...messaging.models.openapi import OpenAPISchema
from ...messaging.valid import GENERIC_DID, UUIDFour


class AnonCredsSchema(BaseModel):
    """AnonCredsSchema"""

    class Meta:
        """AnonCredsSchema metadata."""

        schema_class = "AnonCredsSchemaSchema"

    def __init__(
        self, issuer_id: str, attr_names: List[str], name: str, version: str, **kwargs
    ):
        super().__init__(**kwargs)
        self.issuer_id = issuer_id
        self.attr_names = attr_names
        self.name = name
        self.version = version


class AnonCredsSchemaSchema(BaseModelSchema):
    """Marshmallow schema for indy schema."""

    class Meta:
        """AnonCredsSchemaSchema metadata."""

        model_class = AnonCredsSchema
        unknown = EXCLUDE

    issuer_id = fields.Str(
        description="Issuer Identifier of the credential definition or schema",
        data_key="issuerId",
    )
    attr_names = fields.List(
        fields.Str(
            description="Attribute name",
            example="score",
        ),
        description="Schema attribute names",
        data_key="attrNames",
    )
    name = fields.Str(
        description="Schema name",
        example=ANONCREDS_SCHEMA_ID["example"].split(":")[2],
    )
    version = fields.Str(description="Schema version", **ANONCREDS_VERSION)


class AnonCredsRegistryGetSchema(BaseModel):
    """AnonCredsRegistryGetSchema"""

    class Meta:
        """IndyCredInfo metadata."""

        schema_class = "AnonCredsRegistryGetSchemaSchema"

    def __init__(
        self,
        schema: AnonCredsSchema,
        schema_id: str,
        resolution_metadata: Dict[str, Any],
        schema_metadata: Dict[str, Any],
        **kwargs
    ):
        super().__init__(**kwargs)
        self.schema_ = schema
        self.schema_id = schema_id
        self.resolution_metadata = resolution_metadata
        self.schema_metadata = schema_metadata


class AnonCredsRegistryGetSchemaSchema(BaseModelSchema):
    """Parameters and validators for schema create query."""

    class Meta:
        """AnonCredsRegistryGetSchemaSchema metadata."""

        model_class = AnonCredsRegistryGetSchema
        unknown = EXCLUDE

    schema_ = fields.Nested(AnonCredsSchemaSchema(), data_key="schema")
    schema_id = fields.Str(
        data_key="schemaId", description="Schema identifier", **ANONCREDS_SCHEMA_ID
    )
    resolution_metadata = fields.Dict()
    schema_metadata = fields.Dict()


class SchemaState(OpenAPISchema):
    """Parameters and validators for schema state."""

    state = fields.Str()  # TODO: create validator for only possible states
    schema_id = fields.Str(
        data_key="schemaId", description="Schema identifier", **ANONCREDS_SCHEMA_ID
    )
    schema_ = fields.Nested(AnonCredsSchemaSchema(), data_key="schema")


class SchemasResponseSchema(OpenAPISchema):
    """Parameters and validators for schema list all response."""

    schema_id = fields.List(
        fields.Str(
            data_key="schemaId", description="Schema identifier", **ANONCREDS_SCHEMA_ID
        )
    )


class PostSchemaResponseSchema(OpenAPISchema):
    """Parameters and validators for schema state."""

    job_id = fields.Str()
    schema_state = fields.Nested(SchemaState())
    # For indy, schema_metadata will contain the seqNo
    registration_metadata = fields.Dict()
    schema_metadata = fields.Dict()


class SchemasQueryStringSchema(OpenAPISchema):
    """Parameters and validators for query string in schemas list query."""

    schemaName = fields.Str(
        description="Schema name",
        example=ANONCREDS_SCHEMA_ID["example"].split(":")[2],
    )
    schemaVersion = fields.Str(description="Schema version", **ANONCREDS_VERSION)
    schemaIssuerDid = fields.Str(
        description="Issuer Identifier of the credential definition or schema",
        **GENERIC_DID,
    )  # TODO: get correct validator


class SchemaPostOptionSchema(OpenAPISchema):
    """Parameters and validators for schema options."""

    endorser_connection_id = fields.UUID(
        description="Connection identifier (optional)",
        required=False,
        example=UUIDFour.EXAMPLE,
    )


class SchemaPostQueryStringSchema(OpenAPISchema):
    """Parameters and validators for query string in create schema."""

    schema = fields.Nested(AnonCredsSchemaSchema())
    options = fields.Nested(SchemaPostOptionSchema())
