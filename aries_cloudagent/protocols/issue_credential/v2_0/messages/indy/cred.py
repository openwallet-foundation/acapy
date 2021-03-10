"""Cred artifacts to attach to RFC 453 messages."""

from typing import Mapping, Sequence

from marshmallow import EXCLUDE, fields

from ......messaging.models.base import BaseModel, BaseModelSchema
from ......messaging.valid import (
    INDY_CRED_DEF_ID,
    INDY_DID,
    INDY_SCHEMA_ID,
    NUM_STR_WHOLE,
)


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
        nonce: str = None,
        **kwargs,
    ):
        """Initialize XR cap for indy key correctness proof."""
        super().__init__(**kwargs)

        self.c = c
        self.xz_cap = xz_cap
        self.xr_cap = xr_cap
        self.nonce = nonce


class IndyKeyCorrectnessProofSchema(BaseModelSchema):
    """Indy key correctness proof schema."""

    class Meta:
        """Indy key correctness proof schema metadata."""

        model_class = IndyKeyCorrectnessProof
        unknown = EXCLUDE

    c = fields.Str(
        required=True,
        description="c in key correctness proof",
        **NUM_STR_WHOLE,
    )
    xz_cap = fields.Str(
        required=True,
        description="xz_cap in key correctness proof",
        **NUM_STR_WHOLE,
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
    nonce = fields.Str(
        required=True,
        description="Nonce in key correctness proof",
        **NUM_STR_WHOLE,
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
        **INDY_SCHEMA_ID,
    )
    cred_def_id = fields.Str(
        required=True,
        description="Credential definition identifier",
        **INDY_CRED_DEF_ID,
    )
    nonce = fields.Str(
        required=True,
        description="Nonce in credential abstract",
        **NUM_STR_WHOLE,
    )
    key_correctness_proof = fields.Nested(
        IndyKeyCorrectnessProofSchema(),
        required=True,
        description="Key correctness proof",
    )


class IndyCredRequest(BaseModel):
    """Indy credential request."""

    class Meta:
        """Indy credential request metadata."""

        schema_class = "IndyCredRequestSchema"

    def __init__(
        self,
        prover_did: str = None,
        cred_def_id: str = None,
        blinded_ms: Mapping = None,
        blinded_ms_correctness_proof: Mapping = None,
        nonce: str = None,
        **kwargs,
    ):
        """Initialize indy credential request."""
        super().__init__(**kwargs)
        self.prover_did = prover_did
        self.cred_def_id = cred_def_id
        self.blinded_ms = blinded_ms
        self.blinded_ms_correctness_proof = blinded_ms_correctness_proof
        self.nonce = nonce


class IndyCredRequestSchema(BaseModelSchema):
    """Indy credential request schema."""

    class Meta:
        """Indy credential request schema metadata."""

        model_class = IndyCredRequest
        unknown = EXCLUDE

    prover_did = fields.Str(
        requred=True,
        description="Prover DID",
        **INDY_DID,
    )
    cred_def_id = fields.Str(
        required=True,
        description="Credential definition identifier",
        **INDY_CRED_DEF_ID,
    )
    blinded_ms = fields.Dict(
        required=True,
        description="Blinded master secret",
    )
    blinded_ms_correctness_proof = fields.Dict(
        required=True,
        description="Blinded master secret correctness proof",
    )
    nonce = fields.Str(
        required=True,
        description="Nonce in credential request",
        **NUM_STR_WHOLE,
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

    raw = fields.Str(
        required=True,
        description="Attribute raw value",
    )
    encoded = fields.Str(
        required=True,
        description="Attribute encoded value",
        **NUM_STR_WHOLE,
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
        description="Schema identifier",
        **INDY_SCHEMA_ID,
    )
    cred_def_id = fields.Str(
        required=True,
        description="Credential definition identifier",
        **INDY_CRED_DEF_ID,
    )
    rev_reg_id = fields.Str(
        allow_none=True,
        description="Revocation registry identifier",
        **INDY_CRED_DEF_ID,
    )
    values = fields.Dict(
        keys=fields.Str(description="Attribute name"),
        values=fields.Nested(
            IndyAttrValueSchema(),
            description="Attribute value",
        ),
        required=True,
        description="Credential attributes",
    )
    signature = fields.Dict(
        required=True,
        description="Credential signature",
    )
    signature_correctness_proof = fields.Dict(
        required=True,
        description="Credential signature correctness proof",
    )
    rev_reg = fields.Dict(
        allow_none=True,
        description="Revocation registry state",
    )
    witness = fields.Dict(
        allow_none=True,
        description="Witness for revocation proof",
    )
