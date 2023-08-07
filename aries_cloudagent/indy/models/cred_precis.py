"""Admin routes for presentations."""

from typing import Mapping

from marshmallow import EXCLUDE, fields

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.models.openapi import OpenAPISchema
from ...messaging.valid import (
    INDY_CRED_DEF_ID_EXAMPLE,
    INDY_CRED_DEF_ID_VALIDATE,
    INDY_CRED_REV_ID_EXAMPLE,
    INDY_CRED_REV_ID_VALIDATE,
    INDY_REV_REG_ID_EXAMPLE,
    INDY_REV_REG_ID_VALIDATE,
    INDY_SCHEMA_ID_EXAMPLE,
    INDY_SCHEMA_ID_VALIDATE,
    UUID4_EXAMPLE,
)
from .non_rev_interval import IndyNonRevocationIntervalSchema


class IndyCredInfo(BaseModel):
    """Indy cred info, as holder gets via indy-sdk."""

    class Meta:
        """IndyCredInfo metadata."""

        schema_class = "IndyCredInfoSchema"

    def __init__(
        self,
        referent: str = None,
        attrs: Mapping = None,
        schema_id: str = None,
        cred_def_id: str = None,
        rev_reg_id: str = None,
        cred_rev_id: str = None,
    ):
        """Initialize indy cred info."""
        self.referent = referent
        self.attrs = attrs
        self.schema_id = schema_id
        self.cred_def_id = cred_def_id
        self.rev_reg_id = rev_reg_id
        self.cred_rev_id = cred_rev_id


class IndyCredInfoSchema(BaseModelSchema):
    """Schema for indy cred-info."""

    class Meta:
        """Schema metadata."""

        model_class = IndyCredInfo
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
        validate=INDY_SCHEMA_ID_VALIDATE,
        metadata={
            "description": "Schema identifier",
            "example": INDY_SCHEMA_ID_EXAMPLE,
        },
    )
    cred_def_id = fields.Str(
        validate=INDY_CRED_DEF_ID_VALIDATE,
        metadata={
            "description": "Credential definition identifier",
            "example": INDY_CRED_DEF_ID_EXAMPLE,
        },
    )
    rev_reg_id = fields.Str(
        validate=INDY_REV_REG_ID_VALIDATE,
        allow_none=True,
        metadata={
            "description": "Revocation registry identifier",
            "example": INDY_REV_REG_ID_EXAMPLE,
        },
    )
    cred_rev_id = fields.Str(
        validate=INDY_CRED_REV_ID_VALIDATE,
        allow_none=True,
        metadata={
            "description": "Credential revocation identifier",
            "example": INDY_CRED_REV_ID_EXAMPLE,
        },
    )


class IndyCredPrecisSchema(OpenAPISchema):
    """Schema for precis that indy credential search returns (and aca-py augments)."""

    cred_info = fields.Nested(
        IndyCredInfoSchema(), metadata={"description": "Credential info"}
    )
    interval = fields.Nested(
        IndyNonRevocationIntervalSchema(),
        metadata={"description": "Non-revocation interval from presentation request"},
    )
    presentation_referents = fields.List(
        fields.Str(
            metadata={"description": "presentation referent", "example": "1_age_uuid"}
        )
    )
