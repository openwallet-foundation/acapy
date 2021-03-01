"""Admin routes for presentations."""

from marshmallow import fields

from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import (
    INDY_CRED_DEF_ID,
    INDY_CRED_REV_ID,
    INDY_REV_REG_ID,
    INDY_SCHEMA_ID,
    UUIDFour,
)

from ..indy.proof_request import IndyProofReqNonRevokedSchema


class IndyCredInfoSchema(OpenAPISchema):
    """Schema for indy cred-info."""

    referent = fields.Str(
        description="Wallet referent",
        example=UUIDFour.EXAMPLE,  # typically but not necessarily a UUID4
    )
    attrs = fields.Dict(
        description="Attribute names and value",
        keys=fields.Str(example="age"),  # marshmallow/apispec v3.0 ignores
        values=fields.Str(example="24"),
    )


class IndyCredPrecisSchema(OpenAPISchema):
    """Schema for precis that indy credential search returns (and aca-py augments)."""

    cred_info = fields.Nested(
        IndyCredInfoSchema(),
        description="Credential info",
    )
    schema_id = fields.Str(
        description="Schema identifier",
        **INDY_SCHEMA_ID,
    )
    cred_def_id = fields.Str(
        description="Credential definition identifier",
        **INDY_CRED_DEF_ID,
    )
    rev_reg_id = fields.Str(
        description="Revocation registry identifier",
        **INDY_REV_REG_ID,
    )
    cred_rev = fields.Str(
        description="Credential revocation identifier",
        **INDY_CRED_REV_ID,
    )
    interval = fields.Nested(
        IndyProofReqNonRevokedSchema(),
        description="Non-revocation interval from presentation request",
    )
    pres_referents = fields.List(
        fields.Str(
            description="presentation referent",
            example="1_age_uuid",
        ),
    )
