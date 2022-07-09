"""Schema artifacts."""

from marshmallow import fields

from ...messaging.models.openapi import OpenAPISchema
from ...messaging.valid import IndySchemaId, IndyVersion, NaturalNumber


class SchemaSchema(OpenAPISchema):
    """Marshmallow schema for indy schema."""

    ver = fields.Str(
        description="Node protocol version",
        validate=IndyVersion(),
        example=IndyVersion.EXAMPLE,
    )
    ident = fields.Str(
        data_key="id",
        description="Schema identifier",
        validate=IndySchemaId(),
        example=IndySchemaId.EXAMPLE,
    )
    name = fields.Str(
        description="Schema name",
        example=IndySchemaId.EXAMPLE.split(":")[2],
    )
    version = fields.Str(
        description="Schema version",
        validate=IndyVersion(),
        example=IndyVersion.EXAMPLE,
    )
    attr_names = fields.List(
        fields.Str(
            description="Attribute name",
            example="score",
        ),
        description="Schema attribute names",
        data_key="attrNames",
    )
    seqNo = fields.Int(
        description="Schema sequence number",
        strict=True,
        validate=NaturalNumber(),
        example=NaturalNumber.EXAMPLE,
    )
