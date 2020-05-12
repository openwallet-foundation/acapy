"""Schema utilities."""

from marshmallow import fields, Schema

from ..valid import (
    INDY_DID,
    INDY_SCHEMA_ID,
    INDY_VERSION,
)


class SchemaQueryStringSchema(Schema):
    """Query string parameters for schema searches."""

    schema_id = fields.Str(
        description="Schema identifier", required=False, **INDY_SCHEMA_ID,
    )
    schema_issuer_did = fields.Str(
        description="Schema issuer DID", required=False, **INDY_DID,
    )
    schema_name = fields.Str(
        description="Schema name", required=False, example="membership",
    )
    schema_version = fields.Str(
        description="Schema version", required=False, **INDY_VERSION
    )


SCHEMA_TAGS = [tag for tag in vars(SchemaQueryStringSchema)["_declared_fields"]]
SCHEMA_SENT_RECORD_TYPE = "schema_sent"
