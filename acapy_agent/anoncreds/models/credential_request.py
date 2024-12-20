"""Cred request artifacts to attach to RFC 453 messages."""

from typing import Mapping, Optional

from marshmallow import EXCLUDE, fields

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.valid import (
    ANONCREDS_CRED_DEF_ID_EXAMPLE,
    ANONCREDS_CRED_DEF_ID_VALIDATE,
    NUM_STR_WHOLE_EXAMPLE,
    NUM_STR_WHOLE_VALIDATE,
    UUID4_EXAMPLE,
)


class AnoncredsCredRequest(BaseModel):
    """Anoncreds credential request."""

    class Meta:
        """Anoncreds credential request metadata."""

        schema_class = "AnoncredsCredRequestSchema"

    def __init__(
        self,
        entropy: Optional[str] = None,
        # For compatibility with credx agents, which uses `prover_did` instead of `entropy` # noqa
        prover_did: Optional[str] = None,
        cred_def_id: Optional[str] = None,
        blinded_ms: Optional[Mapping] = None,
        blinded_ms_correctness_proof: Optional[Mapping] = None,
        nonce: Optional[str] = None,
        **kwargs,
    ):
        """Initialize anoncreds credential request."""
        super().__init__(**kwargs)
        self.entropy = entropy
        self.prover_did = prover_did
        self.cred_def_id = cred_def_id
        self.blinded_ms = blinded_ms
        self.blinded_ms_correctness_proof = blinded_ms_correctness_proof
        self.nonce = nonce


class AnoncredsCredRequestSchema(BaseModelSchema):
    """Anoncreds credential request schema."""

    class Meta:
        """Anoncreds credential request schema metadata."""

        model_class = AnoncredsCredRequest
        unknown = EXCLUDE

    entropy = fields.Str(
        required=False,
        metadata={
            "description": "Prover DID/Random String/UUID",
            "example": UUID4_EXAMPLE,
        },
    )
    # For compatibility with credx agents, which uses `prover_did` instead of `entropy`
    prover_did = fields.Str(
        required=False,
        metadata={
            "description": "Prover DID/Random String/UUID",
            "example": UUID4_EXAMPLE,
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
