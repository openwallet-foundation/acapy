"""AnonCreds credential definition models."""

from marshmallow import fields

from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import (
    ANONCREDS_CRED_DEF_ID_EXAMPLE,
    ANONCREDS_DID_EXAMPLE,
    ANONCREDS_SCHEMA_ID_EXAMPLE,
)
from ..common.schemas import EndorserOptionsSchema, SchemaQueryFieldsMixin


class CredIdMatchInfo(OpenAPISchema):
    """Path parameters and validators for request taking credential id."""

    cred_def_id = fields.Str(
        metadata={
            "description": "Credential definition identifier",
            "example": ANONCREDS_CRED_DEF_ID_EXAMPLE,
        },
        required=True,
    )


class InnerCredDefSchema(OpenAPISchema):
    """Parameters and validators for credential definition."""

    tag = fields.Str(
        metadata={
            "description": "Credential definition tag",
            "example": "default",
        },
        required=True,
    )
    schema_id = fields.Str(
        metadata={
            "description": "Schema identifier",
            "example": ANONCREDS_SCHEMA_ID_EXAMPLE,
        },
        required=True,
        data_key="schemaId",
    )
    issuer_id = fields.Str(
        metadata={
            "description": "Issuer Identifier of the credential definition",
            "example": ANONCREDS_DID_EXAMPLE,
        },
        required=True,
        data_key="issuerId",
    )


class CredDefPostOptionsSchema(EndorserOptionsSchema):
    """Parameters and validators for credential definition options."""

    support_revocation = fields.Bool(
        metadata={
            "description": "Support credential revocation",
        },
        required=False,
    )
    revocation_registry_size = fields.Int(
        metadata={
            "description": "Maximum number of credential revocations per registry",
            "example": 1000,
        },
        required=False,
    )


class CredDefPostRequestSchema(OpenAPISchema):
    """Parameters and validators for query string in create credential definition."""

    credential_definition = fields.Nested(InnerCredDefSchema())
    options = fields.Nested(CredDefPostOptionsSchema())
    wait_for_revocation_setup = fields.Boolean(
        required=False,
        load_default=True,
        metadata={
            "description": "Wait for revocation registry setup to complete before returning"  # noqa: E501
        },
    )


class CredDefsQueryStringSchema(SchemaQueryFieldsMixin):
    """Parameters and validators for credential definition list query."""

    issuer_id = fields.Str(
        metadata={
            "description": "Issuer Identifier of the credential definition",
            "example": ANONCREDS_DID_EXAMPLE,
        }
    )
    schema_id = fields.Str(
        metadata={
            "description": "Schema identifier",
            "example": ANONCREDS_SCHEMA_ID_EXAMPLE,
        }
    )


class GetCredDefsResponseSchema(OpenAPISchema):
    """AnonCredsRegistryGetCredDefsSchema."""

    credential_definition_ids = fields.List(
        fields.Str(
            metadata={
                "description": "credential definition identifiers",
                "example": "GvLGiRogTJubmj5B36qhYz:3:CL:8:faber.agent.degree_schema",
            }
        )
    )
