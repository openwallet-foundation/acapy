"""Schema utilities."""

import re

from marshmallow import fields

from ...core.profile import Profile

from ..models.openapi import OpenAPISchema
from ..valid import INDY_DID, INDY_SCHEMA_ID, INDY_VERSION


class SchemaQueryStringSchema(OpenAPISchema):
    """Query string parameters for schema searches."""

    schema_id = fields.Str(
        description="Schema identifier",
        required=False,
        **INDY_SCHEMA_ID,
    )
    schema_issuer_did = fields.Str(
        description="Schema issuer DID",
        required=False,
        **INDY_DID,
    )
    schema_name = fields.Str(
        description="Schema name",
        required=False,
        example="membership",
    )
    schema_version = fields.Str(
        description="Schema version", required=False, **INDY_VERSION
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
