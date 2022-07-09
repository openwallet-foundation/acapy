"""Cred abstract artifacts to attach to RFC 453 messages."""

from typing import Sequence

from marshmallow import EXCLUDE, fields

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.valid import IndyCredDefId, IndySchemaId, NumericStrWhole


class IndyKeyCorrectnessProof(BaseModel):
    """Indy key correctness proof."""

    class Meta:
        """IndyKeyCorrectnessProof metadata."""

        schema_class = "IndyKeyCorrectnessProofSchema"

    def __init__(
        self,
        c: str = None,
        xz_cap: str = None,
        xr_cap: Sequence[Sequence[str]] = None,
        **kwargs,
    ):
        """Initialize XR cap for indy key correctness proof."""
        super().__init__(**kwargs)

        self.c = c
        self.xz_cap = xz_cap
        self.xr_cap = xr_cap


class IndyKeyCorrectnessProofSchema(BaseModelSchema):
    """Indy key correctness proof schema."""

    class Meta:
        """Indy key correctness proof schema metadata."""

        model_class = IndyKeyCorrectnessProof
        unknown = EXCLUDE

    c = fields.Str(
        required=True,
        description="c in key correctness proof",
        validate=NumericStrWhole(),
        example=NumericStrWhole.EXAMPLE,
    )
    xz_cap = fields.Str(
        required=True,
        description="xz_cap in key correctness proof",
        validate=NumericStrWhole(),
        example=NumericStrWhole.EXAMPLE,
    )
    xr_cap = fields.List(
        fields.List(
            fields.Str(
                required=True,
                description="xr_cap component values in key correctness proof",
            ),
            required=True,
            description="xr_cap components in key correctness proof",
            many=True,
        ),
        required=True,
        description="xr_cap in key correctness proof",
        many=True,
    )


class IndyCredAbstract(BaseModel):
    """Indy credential abstract."""

    class Meta:
        """Indy credential abstract metadata."""

        schema_class = "IndyCredAbstractSchema"

    def __init__(
        self,
        schema_id: str = None,
        cred_def_id: str = None,
        nonce: str = None,
        key_correctness_proof: str = None,
        **kwargs,
    ):
        """
        Initialize indy cred abstract object.

        Args:
            schema_id: schema identifier
            cred_def_id: credential definition identifier
            nonce: nonce
            key_correctness_proof: key correctness proof

        """
        super().__init__(**kwargs)
        self.schema_id = schema_id
        self.cred_def_id = cred_def_id
        self.nonce = nonce
        self.key_correctness_proof = key_correctness_proof


class IndyCredAbstractSchema(BaseModelSchema):
    """Indy credential abstract schema."""

    class Meta:
        """Indy credential abstract schema metadata."""

        model_class = IndyCredAbstract
        unknown = EXCLUDE

    schema_id = fields.Str(
        required=True,
        description="Schema identifier",
        validate=IndySchemaId(),
        example=IndySchemaId.EXAMPLE,
    )
    cred_def_id = fields.Str(
        required=True,
        description="Credential definition identifier",
        validate=IndyCredDefId(),
        example=IndyCredDefId.EXAMPLE,
    )
    nonce = fields.Str(
        required=True,
        description="Nonce in credential abstract",
        validate=NumericStrWhole(),
        example=NumericStrWhole.EXAMPLE,
    )
    key_correctness_proof = fields.Nested(
        IndyKeyCorrectnessProofSchema(),
        required=True,
        description="Key correctness proof",
    )
