"""Schema artifacts."""

from marshmallow import fields

from ...messaging.models.openapi import OpenAPISchema
from ...messaging.valid import (
    INDY_SCHEMA_ID_EXAMPLE,
    INDY_SCHEMA_ID_VALIDATE,
    INDY_VERSION_EXAMPLE,
    INDY_VERSION_VALIDATE,
    NATURAL_NUM_EXAMPLE,
    NATURAL_NUM_VALIDATE,
)


class SchemaSchema(OpenAPISchema):
    """Marshmallow schema for indy schema."""

    ver = fields.Str(
        validate=INDY_VERSION_VALIDATE,
        metadata={
            "description": "Node protocol version",
            "example": INDY_VERSION_EXAMPLE,
        },
    )
    ident = fields.Str(
        data_key="id",
        validate=INDY_SCHEMA_ID_VALIDATE,
        metadata={
            "description": "Schema identifier",
            "example": INDY_SCHEMA_ID_EXAMPLE,
        },
    )
    name = fields.Str(
        metadata={
            "description": "Schema name",
            "example": INDY_SCHEMA_ID_EXAMPLE.split(":")[2],
        }
    )
    version = fields.Str(
        validate=INDY_VERSION_VALIDATE,
        metadata={"description": "Schema version", "example": INDY_VERSION_EXAMPLE},
    )
    attr_names = fields.List(
        fields.Str(metadata={"description": "Attribute name", "example": "score"}),
        data_key="attrNames",
        metadata={"description": "Schema attribute names"},
    )
    seqNo = fields.Int(
        validate=NATURAL_NUM_VALIDATE,
        metadata={
            "description": "Schema sequence number",
            "strict": True,
            "example": NATURAL_NUM_EXAMPLE,
        },
    )
