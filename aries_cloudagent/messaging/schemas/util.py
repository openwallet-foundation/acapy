"""Schema utilities."""

import re

from marshmallow import fields

from ...core.profile import Profile

from ..models.openapi import OpenAPISchema
from ..valid import IndyDID, IndySchemaId, IndyVersion


class SchemaQueryStringSchema(OpenAPISchema):
    """Query string parameters for schema searches."""

    schema_id = fields.Str(
        required=False,
        validate=IndySchemaId(),
        metadata={"description": "Schema identifier", "example": IndySchemaId.EXAMPLE},
    )
    schema_issuer_did = fields.Str(
        required=False,
        validate=IndyDID(),
        metadata={"description": "Schema issuer DID", "example": IndyDID.EXAMPLE},
    )
    schema_name = fields.Str(
        required=False, metadata={"description": "Schema name", "example": "membership"}
    )
    schema_version = fields.Str(
        required=False,
        validate=IndyVersion(),
        metadata={"description": "Schema version", "example": IndyVersion.EXAMPLE},
    )


SCHEMA_TAGS = [tag for tag in vars(SchemaQueryStringSchema).get("_declared_fields", [])]
SCHEMA_SENT_RECORD_TYPE = "schema_sent"

SCHEMA_EVENT_PREFIX = "acapy::SCHEMA::"
EVENT_LISTENER_PATTERN = re.compile(f"^{SCHEMA_EVENT_PREFIX}(.*)?$")


async def notify_schema_event(profile: Profile, schema_id: str, meta_data: dict):
    """Send notification for a schema post-process event."""
    await profile.notify(
        SCHEMA_EVENT_PREFIX + schema_id,
        meta_data,
    )
