"""Schema artifacts."""

from marshmallow import fields

from ...messaging.models.openapi import OpenAPISchema
from ...messaging.valid import IndySchemaId, IndyVersion, NaturalNumber


class SchemaSchema(OpenAPISchema):
    """Marshmallow schema for indy schema."""

    ver = fields.Str(
        validate=IndyVersion(),
        metadata={
            "description": "Node protocol version",
            "example": IndyVersion.EXAMPLE,
        },
    )
    ident = fields.Str(
        data_key="id",
        validate=IndySchemaId(),
        metadata={"description": "Schema identifier", "example": IndySchemaId.EXAMPLE},
    )
    name = fields.Str(
        metadata={
            "description": "Schema name",
            "example": IndySchemaId.EXAMPLE.split(":")[2],
        }
    )
    version = fields.Str(
        validate=IndyVersion(),
        metadata={"description": "Schema version", "example": IndyVersion.EXAMPLE},
    )
    attr_names = fields.List(
        fields.Str(metadata={"description": "Attribute name", "example": "score"}),
        data_key="attrNames",
        metadata={"description": "Schema attribute names"},
    )
    seqNo = fields.Int(
        validate=NaturalNumber(),
        metadata={
            "description": "Schema sequence number",
            "strict": True,
            "example": NaturalNumber.EXAMPLE,
        },
    )
