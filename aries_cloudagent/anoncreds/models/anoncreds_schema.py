"""Anoncreds Schema OpenAPI validators"""

from typing import Any, Dict, List, Optional

from marshmallow import EXCLUDE, fields
from marshmallow.validate import OneOf

from ...messaging.models.base import BaseModel, BaseModelSchema


class AnonCredsSchema(BaseModel):
    """An AnonCreds Schema object."""

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
    """Marshmallow schema for anoncreds schema."""

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
    )
    version = fields.Str(description="Schema version")


class GetSchemaResult(BaseModel):
    """Result of resolving a schema."""

    class Meta:
        """GetSchemaResult metadata."""

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


class GetSchemaResultSchema(BaseModelSchema):
    """Parameters and validators for schema create query."""

    class Meta:
        """AnonCredsRegistryGetSchemaSchema metadata."""

        model_class = GetSchemaResult
        unknown = EXCLUDE

    schema_ = fields.Nested(AnonCredsSchemaSchema(), data_key="schema")
    schema_id = fields.Str(data_key="schemaId", description="Schema identifier")
    resolution_metadata = fields.Dict()
    schema_metadata = fields.Dict()


class SchemaState(BaseModel):
    """Model representing the state of a schema after beginning registration."""

    STATE_FINISHED = "finished"
    STATE_FAILED = "failed"
    STATE_ACTION = "action"
    STATE_WAIT = "wait"

    class Meta:
        """SchemaState metadata."""

        schema_class = "SchemaStateSchema"

    def __init__(self, state: str, schema_id: str, schema: AnonCredsSchema, **kwargs):
        """Initialize a new SchemaState."""
        super().__init__(**kwargs)
        self.state = state
        self.schema_id = schema_id
        self.schema = schema


class SchemaStateSchema(BaseModelSchema):
    """Parameters and validators for schema state."""

    class Meta:
        """SchemaStateSchema metadata."""

        model_class = SchemaState

    state = fields.Str(
        validate=OneOf(
            [
                SchemaState.STATE_FINISHED,
                SchemaState.STATE_FAILED,
                SchemaState.STATE_ACTION,
                SchemaState.STATE_WAIT,
            ]
        )
    )
    schema_id = fields.Str(data_key="schemaId", description="Schema identifier")
    schema_ = fields.Nested(AnonCredsSchemaSchema(), data_key="schema")


class SchemaResult(BaseModel):
    """Result of registering a schema."""

    class Meta:
        """SchemaResult metadata."""

        schema_class = "SchemaResultSchema"

    def __init__(
        self,
        job_id: Optional[str],
        schema_state: SchemaState,
        registration_metadata: Optional[dict] = None,
        schema_metadata: Optional[dict] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.job_id = job_id
        self.schema_state = schema_state
        self.registration_metadata = registration_metadata
        self.schema_metadata = schema_metadata


class SchemaResultSchema(BaseModelSchema):
    """Parameters and validators for schema state."""

    class Meta:
        """SchemaResultSchema metadata."""

        model_class = SchemaResult

    job_id = fields.Str()
    schema_state = fields.Nested(SchemaStateSchema())
    registration_metadata = fields.Dict()
    # For indy, schema_metadata will contain the seqNo
    schema_metadata = fields.Dict()
