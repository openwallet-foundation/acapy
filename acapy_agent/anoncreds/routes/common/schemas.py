"""Common schema mixins and definitions for AnonCreds routes."""

from marshmallow import ValidationError, fields, validates_schema

from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import (
    ANONCREDS_CRED_REV_ID_EXAMPLE,
    ANONCREDS_CRED_REV_ID_VALIDATE,
    ANONCREDS_REV_REG_ID_EXAMPLE,
    ANONCREDS_REV_REG_ID_VALIDATE,
    UUID4_EXAMPLE,
    UUID4_VALIDATE,
    UUIDFour,
)

# Field descriptions
endorser_connection_id_description = (
    "Connection identifier (optional) (this is an example). "
    "You can set this if you know the endorser's connection id you want to use. "
    "If not specified then the agent will attempt to find an endorser connection."
)
create_transaction_for_endorser_description = (
    "Create transaction for endorser (optional, default false). "
    "Use this for agents who don't specify an author role but want to "
    "create a transaction for an endorser to sign."
)


class EndorserOptionsSchema(OpenAPISchema):
    """Common schema for endorser-related options."""

    endorser_connection_id = fields.Str(
        metadata={
            "description": endorser_connection_id_description,
            "example": UUIDFour.EXAMPLE,
        },
        required=False,
    )

    create_transaction_for_endorser = fields.Bool(
        metadata={
            "description": create_transaction_for_endorser_description,
            "example": False,
        },
        required=False,
    )


class SchemaQueryFieldsMixin(OpenAPISchema):
    """Mixin for common schema query fields."""

    schema_name = fields.Str(
        metadata={
            "description": "Schema name",
            "example": "example-schema",
        }
    )
    schema_version = fields.Str(
        metadata={
            "description": "Schema version",
            "example": "1.0",
        }
    )


class CredRevRecordQueryStringMixin(OpenAPISchema):
    """Mixin for credential revocation record query string fields."""

    @validates_schema
    def validate_fields(self, data: dict, **kwargs) -> None:
        """Validate schema fields - must have (rr-id and cr-id) xor cx-id."""
        rev_reg_id = data.get("rev_reg_id")
        cred_rev_id = data.get("cred_rev_id")
        cred_ex_id = data.get("cred_ex_id")

        if not (
            (rev_reg_id and cred_rev_id and not cred_ex_id)
            or (cred_ex_id and not rev_reg_id and not cred_rev_id)
        ):
            raise ValidationError(
                "Request must have either rev_reg_id and cred_rev_id or cred_ex_id"
            )

    rev_reg_id = fields.Str(
        required=False,
        validate=ANONCREDS_REV_REG_ID_VALIDATE,
        metadata={
            "description": "Revocation registry identifier",
            "example": ANONCREDS_REV_REG_ID_EXAMPLE,
        },
    )
    cred_rev_id = fields.Str(
        required=False,
        validate=ANONCREDS_CRED_REV_ID_VALIDATE,
        metadata={
            "description": "Credential revocation identifier",
            "example": ANONCREDS_CRED_REV_ID_EXAMPLE,
        },
    )
    cred_ex_id = fields.Str(
        required=False,
        validate=UUID4_VALIDATE,
        metadata={
            "description": "Credential exchange identifier",
            "example": UUID4_EXAMPLE,
        },
    )


class RevRegIdMatchInfoMixin(OpenAPISchema):
    """Mixin for revocation registry ID path parameters."""

    rev_reg_id = fields.Str(
        required=True,
        validate=ANONCREDS_REV_REG_ID_VALIDATE,
        metadata={
            "description": "Revocation Registry identifier",
            "example": ANONCREDS_REV_REG_ID_EXAMPLE,
        },
    )


class RevocationIdsDictMixin(OpenAPISchema):
    """Mixin for revocation IDs dictionary field."""

    rrid2crid = fields.Dict(
        required=False,
        keys=fields.Str(metadata={"example": ANONCREDS_REV_REG_ID_EXAMPLE}),
        values=fields.List(
            fields.Str(
                validate=ANONCREDS_CRED_REV_ID_VALIDATE,
                metadata={
                    "description": "Credential revocation identifier",
                    "example": ANONCREDS_CRED_REV_ID_EXAMPLE,
                },
            )
        ),
        metadata={"description": "Credential revocation ids by revocation registry id"},
    )
