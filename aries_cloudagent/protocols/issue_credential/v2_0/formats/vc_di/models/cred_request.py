"""Cred request artifacts to attach to RFC 453 messages."""

from typing import Mapping, Optional, Union

from marshmallow import EXCLUDE, fields

from .......messaging.models.base import BaseModel, BaseModelSchema
from .......messaging.valid import (
    INDY_CRED_DEF_ID_EXAMPLE,
    INDY_CRED_DEF_ID_VALIDATE,
    INDY_DID_EXAMPLE,
    NUM_STR_WHOLE_EXAMPLE,
    NUM_STR_WHOLE_VALIDATE,
)


class AnoncredsLinkSecretRequest(BaseModel):
    """Binding proof model."""

    class Meta:
        """VCDI credential request schema metadata."""

        schema_class = "BindingProofSchema"

    def __init__(
        self,
        entropy: Optional[str] = None,
        cred_def_id: Optional[str] = None,
        blinded_ms: Optional[Mapping] = None,
        blinded_ms_correctness_proof: Optional[Mapping] = None,
        nonce: Optional[str] = None,
        **kwargs,
    ):
        """Initialize indy credential request."""
        super().__init__(**kwargs)
        self.entropy = entropy
        self.cred_def_id = cred_def_id
        self.blinded_ms = blinded_ms
        self.blinded_ms_correctness_proof = blinded_ms_correctness_proof
        self.nonce = nonce


class AnoncredsLinkSecretSchema(BaseModelSchema):
    """VCDI credential request schema."""

    class Meta:
        """VCDI credential request schema metadata."""

        model_class = AnoncredsLinkSecretRequest
        unknown = EXCLUDE

    entropy = fields.Str(
        required=True,
        validate=str,
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


class DidcommSignedAttachmentRequest(BaseModel):
    """Didcomm Signed Attachment Model."""

    class Meta:
        """Didcomm signed attachment metadata."""

        schema_class = "DidcommSignedAttachmentSchema"

    def __init__(self, attachment_id: Optional[str] = None, **kwargs):
        """Initialize DidcommSignedAttachment."""
        super().__init__(**kwargs)
        self.attachment_id = attachment_id


class DidcommSignedAttachmentSchema(BaseModelSchema):
    """Didcomm Signed Attachment Schema."""

    class Meta:
        """Didcomm Signed Attachment schema metadata."""

        model_class = DidcommSignedAttachmentRequest
        unknown = EXCLUDE

    attachment_id = fields.Str(required=True, metadata={"description": "", "example": ""})


class BindingProof(BaseModel):
    """Binding Proof Model."""

    class Meta:
        """Binding proof metadata."""

        schema_class = "BindingProofSchema"

    def __init__(
        self,
        anoncreds_link_secret: Optional[str] = None,
        didcomm_signed_attachment: Optional[str] = None,
        **kwargs,
    ):
        """Initialize binding proof."""
        super().__init__(**kwargs)
        self.anoncreds_link_secret = anoncreds_link_secret
        self.didcomm_signed_attachment = didcomm_signed_attachment


class BindingProofSchema(BaseModelSchema):
    """Binding Proof Schema."""

    class Meta:
        """Binding proof schema metadata."""

        model_class = BindingProof
        unknown = EXCLUDE

    anoncreds_link_secret = fields.Nested(
        AnoncredsLinkSecretSchema(),
        required=True,
        metadata={"description": "", "example": ""},
    )

    didcomm_signed_attachment = fields.Nested(
        DidcommSignedAttachmentSchema(),
        required=True,
        metadata={"description": "", "example": ""},
    )


class VCDICredRequest(BaseModel):
    """VCDI credential request model."""

    class Meta:
        """VCDI credential request metadata."""

        schema_class = "VCDICredRequestSchema"

    def __init__(
        self,
        data_model_version: Optional[str] = None,
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

    data_model_version = fields.Str(
        required=True, metadata={"description": "", "example": ""}
    )

    binding_proof = fields.Nested(
        BindingProofSchema(),
        required=True,
        metadata={"description": "", "example": ""},
    )
