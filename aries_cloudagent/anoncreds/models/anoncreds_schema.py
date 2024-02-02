"""Anoncreds Schema OpenAPI validators."""

from typing import Any, Dict, List, Optional

from anoncreds import Schema
from marshmallow import EXCLUDE, fields
from marshmallow.validate import OneOf

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.valid import (
    INDY_OR_KEY_DID_EXAMPLE,
    INDY_SCHEMA_ID_EXAMPLE,
)


class AnonCredsSchema(BaseModel):
    """An AnonCreds Schema object."""

    class Meta:
        """AnonCredsSchema metadata."""

        schema_class = "AnonCredsSchemaSchema"

    def __init__(
        self, issuer_id: str, attr_names: List[str], name: str, version: str, **kwargs
    ):
        """Initialize an instance.

        Args:
            issuer_id: Issuer ID
            attr_names: Schema Attribute Name list
            name: Schema name
            version: Schema version

        TODO: update this docstring - Anoncreds-break.

        """
        super().__init__(**kwargs)
        self.issuer_id = issuer_id
        self.attr_names = attr_names
        self.name = name
        self.version = version

    @classmethod
    def from_native(cls, schema: Schema) -> "AnonCredsSchema":
        """Convert from native object."""
        return cls.deserialize(schema.to_dict())

    def to_native(self):
        """Convert to native object."""
        return Schema.load(self.serialize())


class AnonCredsSchemaSchema(BaseModelSchema):
    """Marshmallow schema for anoncreds schema."""

    class Meta:
        """AnonCredsSchemaSchema metadata."""

        model_class = AnonCredsSchema
        unknown = EXCLUDE

    issuer_id = fields.Str(
        metadata={
            "description": "Issuer Identifier of the credential definition or schema",
            "example": INDY_OR_KEY_DID_EXAMPLE,
        },
        data_key="issuerId",
    )
    attr_names = fields.List(
        fields.Str(
            metadata={
                "description": "Attribute name",
                "example": "score",
            }
        ),
        metadata={"description": "Schema attribute names"},
        data_key="attrNames",
    )
    name = fields.Str(
        metadata={"description": "Schema name", "example": "Example schema"}
    )
    version = fields.Str(metadata={"description": "Schema version", "example": "1.0"})


class GetSchemaResult(BaseModel):
    """Result of resolving a schema."""

    class Meta:
        """GetSchemaResult metadata."""

        schema_class = "GetSchemaResultSchema"

    def __init__(
        self,
        schema: AnonCredsSchema,
        schema_id: str,
        resolution_metadata: Dict[str, Any],
        schema_metadata: Dict[str, Any],
        **kwargs
    ):
        """Initialize an instance.

        Args:
            schema: AnonCreds Schema
            schema_id: Schema ID
            resolution_metadata: Resolution Metdata
            schema_metadata: Schema Metadata

        TODO: update this docstring - Anoncreds-break.

        """
        super().__init__(**kwargs)
        self.schema_value = schema
        self.schema_id = schema_id
        self.resolution_metadata = resolution_metadata
        self.schema_metadata = schema_metadata

    @property
    def schema(self) -> AnonCredsSchema:
        """Alias for schema_value.

        `schema` can't be used directly due to a limitation of marshmallow.
        """
        return self.schema_value


class GetSchemaResultSchema(BaseModelSchema):
    """Parameters and validators for schema create query."""

    class Meta:
        """GetSchemaResultSchema metadata."""

        model_class = GetSchemaResult
        unknown = EXCLUDE

    schema_value = fields.Nested(AnonCredsSchemaSchema(), data_key="schema")
    schema_id = fields.Str(
        metadata={"description": "Schema identifier", "example": INDY_SCHEMA_ID_EXAMPLE}
    )
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
        self.schema_value = schema

    @property
    def schema(self) -> AnonCredsSchema:
        """Alias to schema_value.

        `schema` can't be used directly due to limitations of marshmallow.
        """
        return self.schema_value


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
    schema_id = fields.Str(
        metadata={
            "description": "Schema identifier",
            "example": INDY_SCHEMA_ID_EXAMPLE,
        }
    )
    schema_value = fields.Nested(AnonCredsSchemaSchema(), data_key="schema")


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
        """Initialize an instance.

        Args:
            job_id: Job ID
            schema_state: Schema state
            registration_metadata: Registration Metdata
            schema_metadata: Schema Metadata

        TODO: update this docstring - Anoncreds-break.

        """
        super().__init__(**kwargs)
        self.job_id = job_id
        self.schema_state = schema_state
        self.registration_metadata = registration_metadata or {}
        self.schema_metadata = schema_metadata or {}


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
