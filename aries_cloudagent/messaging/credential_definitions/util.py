"""Credential definition utilities."""

import re

from marshmallow import fields

from ...core.profile import Profile
from ..models.openapi import OpenAPISchema
from ..valid import (
    INDY_CRED_DEF_ID_EXAMPLE,
    INDY_CRED_DEF_ID_VALIDATE,
    INDY_DID_EXAMPLE,
    INDY_DID_VALIDATE,
    INDY_SCHEMA_ID_EXAMPLE,
    INDY_SCHEMA_ID_VALIDATE,
    INDY_VERSION_EXAMPLE,
    INDY_VERSION_VALIDATE,
)

CRED_DEF_SENT_RECORD_TYPE = "cred_def_sent"


class CredDefQueryStringSchema(OpenAPISchema):
    """Query string parameters for credential definition searches."""

    schema_id = fields.Str(
        required=False,
        validate=INDY_SCHEMA_ID_VALIDATE,
        metadata={
            "description": "Schema identifier",
            "example": INDY_SCHEMA_ID_EXAMPLE,
        },
    )
    schema_issuer_did = fields.Str(
        required=False,
        validate=INDY_DID_VALIDATE,
        metadata={"description": "Schema issuer DID", "example": INDY_DID_EXAMPLE},
    )
    schema_name = fields.Str(
        required=False, metadata={"description": "Schema name", "example": "membership"}
    )
    schema_version = fields.Str(
        required=False,
        validate=INDY_VERSION_VALIDATE,
        metadata={"description": "Schema version", "example": INDY_VERSION_EXAMPLE},
    )
    issuer_did = fields.Str(
        required=False,
        validate=INDY_DID_VALIDATE,
        metadata={"description": "Issuer DID", "example": INDY_DID_EXAMPLE},
    )
    cred_def_id = fields.Str(
        required=False,
        validate=INDY_CRED_DEF_ID_VALIDATE,
        metadata={
            "description": "Credential definition id",
            "example": INDY_CRED_DEF_ID_EXAMPLE,
        },
    )


CRED_DEF_TAGS = [
    tag for tag in vars(CredDefQueryStringSchema).get("_declared_fields", [])
]

CRED_DEF_EVENT_PREFIX = "acapy::CRED_DEF::"
EVENT_LISTENER_PATTERN = re.compile(f"^{CRED_DEF_EVENT_PREFIX}(.*)?$")


async def notify_cred_def_event(profile: Profile, cred_def_id: str, meta_data: dict):
    """Send notification for a cred def post-process event."""
    await profile.notify(
        CRED_DEF_EVENT_PREFIX + cred_def_id,
        meta_data,
    )
