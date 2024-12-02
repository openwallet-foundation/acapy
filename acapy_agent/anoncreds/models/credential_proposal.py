"""Anoncreds credential definition proposal."""

import re

from marshmallow import fields

from ...core.profile import Profile
from ...messaging.models.openapi import OpenAPISchema
from ...messaging.valid import (
    ANONCREDS_CRED_DEF_ID_EXAMPLE,
    ANONCREDS_CRED_DEF_ID_VALIDATE,
    ANONCREDS_DID_EXAMPLE,
    ANONCREDS_DID_VALIDATE,
    ANONCREDS_SCHEMA_ID_EXAMPLE,
    ANONCREDS_SCHEMA_ID_VALIDATE,
)


class AnoncredsCredentialDefinitionProposal(OpenAPISchema):
    """Query string parameters for credential definition searches."""

    schema_id = fields.Str(
        required=False,
        validate=ANONCREDS_SCHEMA_ID_VALIDATE,
        metadata={
            "description": "Schema identifier",
            "example": ANONCREDS_SCHEMA_ID_EXAMPLE,
        },
    )
    issuer_id = fields.Str(
        required=False,
        validate=ANONCREDS_DID_VALIDATE,
        metadata={"description": "Issuer DID", "example": ANONCREDS_DID_EXAMPLE},
    )
    cred_def_id = fields.Str(
        required=False,
        validate=ANONCREDS_CRED_DEF_ID_VALIDATE,
        metadata={
            "description": "Credential definition id",
            "example": ANONCREDS_CRED_DEF_ID_EXAMPLE,
        },
    )


CRED_DEF_TAGS = list(
    vars(AnoncredsCredentialDefinitionProposal).get("_declared_fields", [])
)

CRED_DEF_EVENT_PREFIX = "acapy::CRED_DEF::"
EVENT_LISTENER_PATTERN = re.compile(f"^{CRED_DEF_EVENT_PREFIX}(.*)?$")


async def notify_cred_def_event(profile: Profile, cred_def_id: str, meta_data: dict):
    """Send notification for a cred def post-process event."""
    await profile.notify(
        CRED_DEF_EVENT_PREFIX + cred_def_id,
        meta_data,
    )
