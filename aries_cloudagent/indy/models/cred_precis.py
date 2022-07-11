"""Admin routes for presentations."""

from typing import Mapping

from marshmallow import EXCLUDE, fields

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.models.openapi import OpenAPISchema
from ...messaging.valid import (
    IndyCredDefId,
    IndyCredRevId,
    IndyRevRegId,
    IndySchemaId,
    UUIDFour,
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
        metadata={"description": "Wallet referent", "example": UUIDFour.EXAMPLE}
    )
    attrs = fields.Dict(
        keys=fields.Str(metadata={"example": "userid"}),
        values=fields.Str(metadata={"example": "alice"}),
        metadata={"description": "Attribute names and value"},
    )
    schema_id = fields.Str(
        validate=IndySchemaId(),
        metadata={"description": "Schema identifier", "example": IndySchemaId.EXAMPLE},
    )
    cred_def_id = fields.Str(
        validate=IndyCredDefId(),
        metadata={
            "description": "Credential definition identifier",
            "example": IndyCredDefId.EXAMPLE,
        },
    )
    rev_reg_id = fields.Str(
        validate=IndyRevRegId(),
        allow_none=True,
        metadata={
            "description": "Revocation registry identifier",
            "example": IndyRevRegId.EXAMPLE,
        },
    )
    cred_rev_id = fields.Str(
        validate=IndyCredRevId(),
        allow_none=True,
        metadata={
            "description": "Credential revocation identifier",
            "example": IndyCredRevId.EXAMPLE,
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
