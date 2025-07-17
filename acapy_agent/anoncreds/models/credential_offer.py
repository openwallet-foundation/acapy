"""AnonCreds Credential Offer format for v2.0 of the issue-credential protocol."""

from typing import Optional, Sequence

from marshmallow import EXCLUDE, fields

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.valid import (
    ANONCREDS_CRED_DEF_ID_EXAMPLE,
    ANONCREDS_CRED_DEF_ID_VALIDATE,
    ANONCREDS_SCHEMA_ID_EXAMPLE,
    ANONCREDS_SCHEMA_ID_VALIDATE,
    NUM_STR_WHOLE_EXAMPLE,
    NUM_STR_WHOLE_VALIDATE,
)


class AnonCredsKeyCorrectnessProof(BaseModel):
    """AnonCreds key correctness proof."""

    class Meta:
        """AnonCredsKeyCorrectnessProof metadata."""

        schema_class = "AnonCredsKeyCorrectnessProofSchema"

    def __init__(
        self,
        c: Optional[str] = None,
        xz_cap: Optional[str] = None,
        xr_cap: Optional[Sequence[Sequence[str]]] = None,
        **kwargs,
    ):
        """Initialize XR cap for anoncreds key correctness proof."""
        super().__init__(**kwargs)

        self.c = c
        self.xz_cap = xz_cap
        self.xr_cap = xr_cap


class AnonCredsCorrectnessProofSchema(BaseModelSchema):
    """AnonCreds key correctness proof schema."""

    class Meta:
        """AnonCreds key correctness proof schema metadata."""

        model_class = AnonCredsKeyCorrectnessProof
        unknown = EXCLUDE

    c = fields.Str(
        required=True,
        validate=NUM_STR_WHOLE_VALIDATE,
        metadata={
            "description": "c in key correctness proof",
            "example": NUM_STR_WHOLE_EXAMPLE,
        },
    )
    xz_cap = fields.Str(
        required=True,
        validate=NUM_STR_WHOLE_VALIDATE,
        metadata={
            "description": "xz_cap in key correctness proof",
            "example": NUM_STR_WHOLE_EXAMPLE,
        },
    )
    xr_cap = fields.List(
        fields.List(
            fields.Str(
                required=True,
                metadata={
                    "description": "xr_cap component values in key correctness proof"
                },
            ),
            required=True,
            metadata={
                "description": "xr_cap components in key correctness proof",
                "many": True,
            },
        ),
        required=True,
        metadata={"description": "xr_cap in key correctness proof", "many": True},
    )


class AnonCredsCredentialOffer(BaseModel):
    """AnonCreds Credential Offer."""

    class Meta:
        """AnonCredsCredentialOffer metadata."""

        schema_class = "AnonCredsCredentialOfferSchema"

    def __init__(
        self,
        schema_id: Optional[str] = None,
        cred_def_id: Optional[str] = None,
        nonce: Optional[str] = None,
        key_correctness_proof: Optional[str] = None,
        **kwargs,
    ):
        """Initialize values ."""
        super().__init__(**kwargs)
        self.schema_id = schema_id
        self.cred_def_id = cred_def_id
        self.nonce = nonce
        self.key_correctness_proof = key_correctness_proof


class AnonCredsCredentialOfferSchema(BaseModelSchema):
    """AnonCreds Credential Offer Schema."""

    class Meta:
        """AnonCredsCredentialOffer schema metadata."""

        model_class = AnonCredsCredentialOffer
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

    nonce = fields.Str(
        required=True,
        validate=NUM_STR_WHOLE_VALIDATE,
        metadata={
            "description": "Nonce in credential abstract",
            "example": NUM_STR_WHOLE_EXAMPLE,
        },
    )

    key_correctness_proof = fields.Nested(
        AnonCredsCorrectnessProofSchema(),
        required=True,
        metadata={"description": "Key correctness proof"},
    )
