"""AnonCreds credential definition proposal."""

import re

from marshmallow import fields, validate

from ...core.profile import Profile
from ...messaging.models.openapi import OpenAPISchema
from ...messaging.valid import (
    ANONCREDS_CRED_DEF_ID_EXAMPLE,
    ANONCREDS_CRED_DEF_ID_VALIDATE,
    ANONCREDS_DID_EXAMPLE,
    ANONCREDS_DID_VALIDATE,
    ANONCREDS_SCHEMA_ID_EXAMPLE,
    ANONCREDS_SCHEMA_ID_VALIDATE,
    INDY_DID_VALIDATE,
    MAJOR_MINOR_VERSION_EXAMPLE,
    MAJOR_MINOR_VERSION_VALIDATE,
)


class AnonCredsCredentialDefinitionProposal(OpenAPISchema):
    """Query string parameters for credential definition searches."""

    cred_def_id = fields.Str(
        required=False,
        validate=ANONCREDS_CRED_DEF_ID_VALIDATE,
        metadata={
            "description": "Credential definition id. This is the only required field.",
            "example": ANONCREDS_CRED_DEF_ID_EXAMPLE,
        },
    )
    issuer_id = fields.Str(
        required=False,
        # TODO: INDY_DID_VALIDATE should be removed when indy sov did's
        # are represented by did:sov:{nym} in acapy
        validate=validate.NoneOf([ANONCREDS_DID_VALIDATE, INDY_DID_VALIDATE]),
        metadata={"description": "Issuer DID", "example": ANONCREDS_DID_EXAMPLE},
    )
    schema_id = fields.Str(
        required=False,
        validate=ANONCREDS_SCHEMA_ID_VALIDATE,
        metadata={
            "description": "Schema identifier",
            "example": ANONCREDS_SCHEMA_ID_EXAMPLE,
        },
    )
    schema_issuer_id = fields.Str(
        required=False,
        # TODO: INDY_DID_VALIDATE should be removed when indy sov did's
        # are represented by did:sov:{nym} in acapy
        validate=validate.NoneOf([ANONCREDS_DID_VALIDATE, INDY_DID_VALIDATE]),
        metadata={
            "description": "Schema identifier",
            "example": ANONCREDS_SCHEMA_ID_EXAMPLE,
        },
    )
    schema_name = fields.Str(
        required=False, metadata={"description": "Schema name", "example": "simple"}
    )
    schema_version = fields.Str(
        required=False,
        validate=MAJOR_MINOR_VERSION_VALIDATE,
        metadata={
            "description": "Schema version",
            "example": MAJOR_MINOR_VERSION_EXAMPLE,
        },
    )


CRED_DEF_TAGS = list(
    vars(AnonCredsCredentialDefinitionProposal).get("_declared_fields", [])
)

CRED_DEF_EVENT_PREFIX = "acapy::CRED_DEF::"
EVENT_LISTENER_PATTERN = re.compile(f"^{CRED_DEF_EVENT_PREFIX}(.*)?$")


async def notify_cred_def_event(
    profile: Profile, cred_def_id: str, meta_data: dict
) -> None:
    """Send notification for a cred def post-process event."""
    await profile.notify(
        CRED_DEF_EVENT_PREFIX + cred_def_id,
        meta_data,
    )
