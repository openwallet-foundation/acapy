"""Credential definition utilities."""

import re

from marshmallow import fields

from ....core.profile import Profile
from ...models.openapi import OpenAPISchema
from ...valid import (
    VCDI_CRED_DEF_ID_EXAMPLE,
    VCDI_CRED_DEF_ID_VALIDATE,
    VCDI_DID_EXAMPLE,
    VCDI_DID_VALIDATE,
    VCDI_SCHEMA_ID_EXAMPLE,
    VCDI_SCHEMA_ID_VALIDATE,
    VCDI_VERSION_EXAMPLE,
    VCDI_VERSION_VALIDATE,
)

CRED_DEF_SENT_RECORD_TYPE = "cred_def_sent"


class VCDICredDefQueryStringSchema(OpenAPISchema):
    """Query string parameters for credential definition searches."""

    schema_id = fields.Str(
        required=False,
        validate=VCDI_SCHEMA_ID_VALIDATE,
        metadata={
            "description": "Schema identifier",
            "example": VCDI_SCHEMA_ID_EXAMPLE,
        },
    )
    schema_issuer_did = fields.Str(
        required=False,
        validate=VCDI_DID_VALIDATE,
        metadata={"description": "Schema issuer DID", "example": VCDI_DID_EXAMPLE},
    )
    schema_name = fields.Str(
        required=False, metadata={"description": "Schema name", "example": "membership"}
    )
    schema_version = fields.Str(
        required=False,
        validate=VCDI_VERSION_VALIDATE,
        metadata={"description": "Schema version", "example": VCDI_VERSION_EXAMPLE},
    )
    issuer_did = fields.Str(
        required=False,
        validate=VCDI_DID_VALIDATE,
        metadata={"description": "Issuer DID", "example": VCDI_DID_EXAMPLE},
    )
    cred_def_id = fields.Str(
        required=False,
        validate=VCDI_CRED_DEF_ID_VALIDATE,
        metadata={
            "description": "Credential definition id",
            "example": VCDI_CRED_DEF_ID_EXAMPLE,
        },
    )


CRED_DEF_TAGS = list(vars(VCDICredDefQueryStringSchema).get("_declared_fields", []))

CRED_DEF_EVENT_PREFIX = "acapy::CRED_DEF::"
EVENT_LISTENER_PATTERN = re.compile(f"^{CRED_DEF_EVENT_PREFIX}(.*)?$")


async def notify_cred_def_event(profile: Profile, cred_def_id: str, meta_data: dict):
    """Send notification for a cred def post-process event."""
    await profile.notify(
        CRED_DEF_EVENT_PREFIX + cred_def_id,
        meta_data,
    )