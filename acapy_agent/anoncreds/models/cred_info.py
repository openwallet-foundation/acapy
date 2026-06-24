"""Credential info model for AnonCreds holder credentials."""

from typing import Mapping, Optional

from marshmallow import EXCLUDE, fields

from acapy_agent.messaging.models.base import BaseModel, BaseModelSchema
from acapy_agent.messaging.models.openapi import OpenAPISchema
from acapy_agent.messaging.valid import (
    ANONCREDS_CRED_DEF_ID_EXAMPLE,
    ANONCREDS_CRED_DEF_ID_VALIDATE,
    ANONCREDS_CRED_REV_ID_EXAMPLE,
    ANONCREDS_CRED_REV_ID_VALIDATE,
    ANONCREDS_REV_REG_ID_EXAMPLE,
    ANONCREDS_REV_REG_ID_VALIDATE,
    ANONCREDS_SCHEMA_ID_EXAMPLE,
    ANONCREDS_SCHEMA_ID_VALIDATE,
    UUID4_EXAMPLE,
)

from .non_rev_interval import AnonCredsNonRevocationInterval


class CredInfo(BaseModel):
    """Indy cred info, as holder gets via indy-sdk."""

    class Meta:
        """IndyCredInfo metadata."""

        schema_class = "IndyCredInfoSchema"

    def __init__(
        self,
        referent: Optional[str] = None,
        attrs: Optional[Mapping] = None,
        schema_id: Optional[str] = None,
        cred_def_id: Optional[str] = None,
        rev_reg_id: Optional[str] = None,
        cred_rev_id: Optional[str] = None,
    ):
        """Initialize indy cred info."""
        self.referent = referent
        self.attrs = attrs
        self.schema_id = schema_id
        self.cred_def_id = cred_def_id
        self.rev_reg_id = rev_reg_id
        self.cred_rev_id = cred_rev_id


class CredInfoSchema(BaseModelSchema):
    """Schema for indy cred-info."""

    class Meta:
        """Schema metadata."""

        model_class = CredInfo
        unknown = EXCLUDE

    referent = fields.Str(
        metadata={"description": "Wallet referent", "example": UUID4_EXAMPLE}
    )
    attrs = fields.Dict(
        keys=fields.Str(metadata={"example": "userid"}),
        values=fields.Str(metadata={"example": "alice"}),
        metadata={"description": "Attribute names and value"},
    )
    schema_id = fields.Str(
        validate=ANONCREDS_SCHEMA_ID_VALIDATE,
        metadata={
            "description": "Schema identifier",
            "example": ANONCREDS_SCHEMA_ID_EXAMPLE,
        },
    )
    cred_def_id = fields.Str(
        validate=ANONCREDS_CRED_DEF_ID_VALIDATE,
        metadata={
            "description": "Credential definition identifier",
            "example": ANONCREDS_CRED_DEF_ID_EXAMPLE,
        },
    )
    rev_reg_id = fields.Str(
        validate=ANONCREDS_REV_REG_ID_VALIDATE,
        allow_none=True,
        metadata={
            "description": "Revocation registry identifier",
            "example": ANONCREDS_REV_REG_ID_EXAMPLE,
        },
    )
    cred_rev_id = fields.Str(
        validate=ANONCREDS_CRED_REV_ID_VALIDATE,
        allow_none=True,
        metadata={
            "description": "Credential revocation identifier",
            "example": ANONCREDS_CRED_REV_ID_EXAMPLE,
        },
    )


class CredPrecisSchema(OpenAPISchema):
    """Schema for precis that indy credential search returns (and aca-py augments)."""

    cred_info = fields.Nested(
        CredInfoSchema(),
        metadata={"description": "Credential info"},
        required=True,
    )
    interval = fields.Nested(
        AnonCredsNonRevocationInterval(),
        metadata={"description": "Non-revocation interval from presentation request"},
    )
    presentation_referents = fields.List(
        fields.Str(
            required=True,
            metadata={"description": "presentation referent", "example": "1_age_uuid"},
        )
    )
