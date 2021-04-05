"""Credential definition utilities."""

from marshmallow import fields

from ..models.openapi import OpenAPISchema
from ..valid import (
    INDY_DID,
    INDY_CRED_DEF_ID,
    INDY_SCHEMA_ID,
    INDY_VERSION,
)


CRED_DEF_SENT_RECORD_TYPE = "cred_def_sent"


class CredDefQueryStringSchema(OpenAPISchema):
    """Query string parameters for credential definition searches."""

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
    issuer_did = fields.Str(
        description="Issuer DID",
        required=False,
        **INDY_DID,
    )
    cred_def_id = fields.Str(
        description="Credential definition id",
        required=False,
        **INDY_CRED_DEF_ID,
    )


CRED_DEF_TAGS = [
    tag for tag in vars(CredDefQueryStringSchema).get("_declared_fields", [])
]
