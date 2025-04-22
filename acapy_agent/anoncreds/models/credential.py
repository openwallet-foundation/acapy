"""Credential artifacts."""

from typing import Mapping, Optional

from marshmallow import EXCLUDE, ValidationError, fields

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.valid import (
    ANONCREDS_CRED_DEF_ID_EXAMPLE,
    ANONCREDS_CRED_DEF_ID_VALIDATE,
    ANONCREDS_REV_REG_ID_EXAMPLE,
    ANONCREDS_REV_REG_ID_VALIDATE,
    ANONCREDS_SCHEMA_ID_EXAMPLE,
    ANONCREDS_SCHEMA_ID_VALIDATE,
    NUM_STR_ANY_EXAMPLE,
    NUM_STR_ANY_VALIDATE,
)


class AnonCredsAttrValue(BaseModel):
    """AnonCreds attribute value."""

    class Meta:
        """AnonCreds attribute value."""

        schema_class = "AnonCredsAttrValueSchema"

    def __init__(
        self, raw: Optional[str] = None, encoded: Optional[str] = None, **kwargs
    ):
        """Initialize anoncreds (credential) attribute value."""
        super().__init__(**kwargs)
        self.raw = raw
        self.encoded = encoded


class AnonCredsAttrValueSchema(BaseModelSchema):
    """AnonCreds attribute value schema."""

    class Meta:
        """AnonCreds attribute value schema metadata."""

        model_class = AnonCredsAttrValue
        unknown = EXCLUDE

    raw = fields.Str(required=True, metadata={"description": "Attribute raw value"})
    encoded = fields.Str(
        required=True,
        validate=NUM_STR_ANY_VALIDATE,
        metadata={
            "description": "Attribute encoded value",
            "example": NUM_STR_ANY_EXAMPLE,
        },
    )


class DictWithAnonCredsAttrValueSchema(fields.Dict):
    """Dict with anoncreds attribute value schema."""

    def __init__(self, **kwargs):
        """Initialize the custom schema for a dictionary with AnonCredsAttrValue."""
        super().__init__(
            keys=fields.Str(metadata={"description": "Attribute name"}),
            values=fields.Nested(AnonCredsAttrValueSchema()),
            **kwargs,
        )

    def _deserialize(self, value: dict, attr: str, data: dict, **kwargs) -> dict:
        """Deserialize dict with anoncreds attribute value."""
        if not isinstance(value, dict):
            raise ValidationError("Value must be a dict.")

        errors = {}
        anoncreds_attr_value_schema = AnonCredsAttrValueSchema()

        for k, v in value.items():
            if isinstance(v, dict):
                validation_errors = anoncreds_attr_value_schema.validate(v)
                if validation_errors:
                    errors[k] = validation_errors

        if errors:
            raise ValidationError(errors)

        return value


class AnonCredsCredential(BaseModel):
    """AnonCreds credential."""

    class Meta:
        """AnonCreds credential metadata."""

        schema_class = "AnonCredsCredentialSchema"

    def __init__(
        self,
        schema_id: Optional[str] = None,
        cred_def_id: Optional[str] = None,
        rev_reg_id: Optional[str] = None,
        values: Mapping[str, AnonCredsAttrValue] = None,
        signature: Optional[Mapping] = None,
        signature_correctness_proof: Optional[Mapping] = None,
        rev_reg: Optional[Mapping] = None,
        witness: Optional[Mapping] = None,
    ):
        """Initialize anoncreds credential."""
        self.schema_id = schema_id
        self.cred_def_id = cred_def_id
        self.rev_reg_id = rev_reg_id
        self.values = values
        self.signature = signature
        self.signature_correctness_proof = signature_correctness_proof
        self.rev_reg = rev_reg
        self.witness = witness


class AnonCredsCredentialSchema(BaseModelSchema):
    """AnonCreds credential schema."""

    class Meta:
        """AnonCreds credential schemametadata."""

        model_class = AnonCredsCredential
        unknown = EXCLUDE

    schema_id = fields.Str(
        required=True,
        validate=ANONCREDS_SCHEMA_ID_VALIDATE,
        metadata={
            "description": "Schema identifier",
            "example": ANONCREDS_SCHEMA_ID_EXAMPLE,
        },
    )
    cred_def_id = fields.Str(
        required=True,
        validate=ANONCREDS_CRED_DEF_ID_VALIDATE,
        metadata={
            "description": "Credential definition identifier",
            "example": ANONCREDS_CRED_DEF_ID_EXAMPLE,
        },
    )
    rev_reg_id = fields.Str(
        allow_none=True,
        validate=ANONCREDS_REV_REG_ID_VALIDATE,
        metadata={
            "description": "Revocation registry identifier",
            "example": ANONCREDS_REV_REG_ID_EXAMPLE,
        },
    )
    values = DictWithAnonCredsAttrValueSchema(
        required=True,
        metadata={"description": "Credential attributes"},
    )
    signature = fields.Dict(
        required=True, metadata={"description": "Credential signature"}
    )
    signature_correctness_proof = fields.Dict(
        required=True,
        metadata={"description": "Credential signature correctness proof"},
    )
    rev_reg = fields.Dict(
        allow_none=True, metadata={"description": "Revocation registry state"}
    )
    witness = fields.Dict(
        allow_none=True, metadata={"description": "Witness for revocation proof"}
    )
