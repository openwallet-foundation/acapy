"""Credential artifacts."""

from typing import Mapping

from marshmallow import EXCLUDE, fields

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.valid import (
    IndyCredDefId,
    IndyRevRegId,
    IndySchemaId,
    NumericStrAny,
)


class IndyAttrValue(BaseModel):
    """Indy attribute value."""

    class Meta:
        """Indy attribute value."""

        schema_class = "IndyAttrValueSchema"

    def __init__(self, raw: str = None, encoded: str = None, **kwargs):
        """Initialize indy (credential) attribute value."""
        super().__init__(**kwargs)
        self.raw = raw
        self.encoded = encoded


class IndyAttrValueSchema(BaseModelSchema):
    """Indy attribute value schema."""

    class Meta:
        """Indy attribute value schema metadata."""

        model_class = IndyAttrValue
        unknown = EXCLUDE

    raw = fields.Str(required=True, metadata={"description": "Attribute raw value"})
    encoded = fields.Str(
        required=True,
        validate=NumericStrAny(),
        metadata={
            "description": "Attribute encoded value",
            "example": NumericStrAny.EXAMPLE,
        },
    )


class IndyCredential(BaseModel):
    """Indy credential."""

    class Meta:
        """Indy credential metadata."""

        schema_class = "IndyCredentialSchema"

    def __init__(
        self,
        schema_id: str = None,
        cred_def_id: str = None,
        rev_reg_id: str = None,
        values: Mapping[str, IndyAttrValue] = None,
        signature: Mapping = None,
        signature_correctness_proof: Mapping = None,
        rev_reg: Mapping = None,
        witness: Mapping = None,
    ):
        """Initialize indy credential."""
        self.schema_id = schema_id
        self.cred_def_id = cred_def_id
        self.rev_reg_id = rev_reg_id
        self.values = values
        self.signature = signature
        self.signature_correctness_proof = signature_correctness_proof
        self.rev_reg = rev_reg
        self.witness = witness


class IndyCredentialSchema(BaseModelSchema):
    """Indy credential schema."""

    class Meta:
        """Indy credential schemametadata."""

        model_class = IndyCredential
        unknown = EXCLUDE

    schema_id = fields.Str(
        required=True,
        validate=IndySchemaId(),
        metadata={"description": "Schema identifier", "example": IndySchemaId.EXAMPLE},
    )
    cred_def_id = fields.Str(
        required=True,
        validate=IndyCredDefId(),
        metadata={
            "description": "Credential definition identifier",
            "example": IndyCredDefId.EXAMPLE,
        },
    )
    rev_reg_id = fields.Str(
        allow_none=True,
        validate=IndyRevRegId(),
        metadata={
            "description": "Revocation registry identifier",
            "example": IndyRevRegId.EXAMPLE,
        },
    )
    values = fields.Dict(
        keys=fields.Str(metadata={"description": "Attribute name"}),
        values=fields.Nested(
            IndyAttrValueSchema(), metadata={"description": "Attribute value"}
        ),
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
