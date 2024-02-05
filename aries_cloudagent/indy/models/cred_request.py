"""Cred request artifacts to attach to RFC 453 messages."""

from typing import Mapping, Union

from marshmallow import EXCLUDE, fields

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.valid import (
    INDY_CRED_DEF_ID_EXAMPLE,
    INDY_CRED_DEF_ID_VALIDATE,
    UUID4_EXAMPLE,
    NUM_STR_WHOLE_EXAMPLE,
    NUM_STR_WHOLE_VALIDATE,
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
        required=True,
        metadata={
            "description": "Prover DID/Random String/UUID",
            "example": UUID4_EXAMPLE,
        },
    )
    cred_def_id = fields.Str(
        required=True,
        validate=INDY_CRED_DEF_ID_VALIDATE,
        metadata={
            "description": "Credential definition identifier",
            "example": INDY_CRED_DEF_ID_EXAMPLE,
        },
    )
    blinded_ms = fields.Dict(
        required=True, metadata={"description": "Blinded master secret"}
    )
    blinded_ms_correctness_proof = fields.Dict(
        required=True,
        metadata={"description": "Blinded master secret correctness proof"},
    )
    nonce = fields.Str(
        required=True,
        validate=NUM_STR_WHOLE_VALIDATE,
        metadata={
            "description": "Nonce in credential request",
            "example": NUM_STR_WHOLE_EXAMPLE,
        },
    )


class BindingProof(BaseModel):
    """Binding proof model."""

    class Meta:
        """VCDI credential request schema metadata."""

        schema_class = "BindingProofSchema"

    def __init__(
        self,
        entropy: str = None,
        cred_def_id: str = None,
        blinded_ms: Mapping = None,
        blinded_ms_correctness_proof: Mapping = None,
        nonce: str = None,
        **kwargs,
    ):
        """Initialize indy credential request."""
        super().__init__(**kwargs)
        self.entropy = entropy
        self.cred_def_id = cred_def_id
        self.blinded_ms = blinded_ms
        self.blinded_ms_correctness_proof = blinded_ms_correctness_proof
        self.nonce = nonce


class BindingProofSchema(BaseModelSchema):
    """VCDI credential request schema."""

    class Meta:
        """VCDI credential request schema metadata."""

        model_class = BindingProof
        unknown = EXCLUDE

    entropy = fields.Str(
        required=True,
        validate=INDY_DID_VALIDATE,
        metadata={"description": "Prover DID", "example": INDY_DID_EXAMPLE},
    )
    cred_def_id = fields.Str(
        required=True,
        validate=INDY_CRED_DEF_ID_VALIDATE,
        metadata={
            "description": "Credential definition identifier",
            "example": INDY_CRED_DEF_ID_EXAMPLE,
        },
    )
    blinded_ms = fields.Dict(
        required=True, metadata={"description": "Blinded master secret"}
    )
    blinded_ms_correctness_proof = fields.Dict(
        required=True,
        metadata={"description": "Blinded master secret correctness proof"},
    )
    nonce = fields.Str(
        required=True,
        validate=NUM_STR_WHOLE_VALIDATE,
        metadata={
            "description": "Nonce in credential request",
            "example": NUM_STR_WHOLE_EXAMPLE,
        },
    )


class VCDICredRequest(BaseModel):
    """VCDI credential request model."""

    class Meta:
        """VCDI credential request metadata."""

        schema_class = "VCDICredRequestSchema"

    def __init__(
        self,
        data_model_version: str = None,
        binding_proof: Union[dict, BindingProof] = None,
        **kwargs,
    ):
        """Initialize values for VCDICredRequest."""
        super().__init__(**kwargs)
        self.data_model_version = data_model_version
        self.binding_proof = binding_proof


class VCDICredRequestSchema(BaseModelSchema):
    """VCDI credential request schema."""

    class Meta:
        """VCDI credential request schema metadata."""

        model_class = VCDICredRequest
        unknown = EXCLUDE

    data_model_version = fields.str(
        required=True, metadata={"description": "", "example": ""}
    )

    binding_proof = fields.str(required=True, metadata={"description": "", "example": ""})
