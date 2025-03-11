"""Cred request artifacts to attach to RFC 453 messages."""

from typing import Optional, Sequence, Union

from marshmallow import EXCLUDE, fields

from .......indy.models.cred_abstract import IndyKeyCorrectnessProofSchema
from .......messaging.models.base import BaseModel, BaseModelSchema
from .......messaging.valid import (
    INDY_CRED_DEF_ID_EXAMPLE,
    INDY_CRED_DEF_ID_VALIDATE,
    NUM_STR_WHOLE_EXAMPLE,
    NUM_STR_WHOLE_VALIDATE,
)
from .......vc.vc_ld.models.credential import CredentialSchema, VerifiableCredential


class AnonCredsLinkSecret(BaseModel):
    """AnonCreds Link Secret Model."""

    class Meta:
        """AnonCredsLinkSecret metadata."""

        schema_class = "AnonCredsLinkSecretSchema"

    def __init__(
        self,
        nonce: Optional[str] = None,
        cred_def_id: Optional[str] = None,
        key_correctness_proof: Optional[str] = None,
        **kwargs,
    ):
        """Initialize values for AnonCredsLinkSecret."""
        super().__init__(**kwargs)
        self.nonce = nonce
        self.cred_def_id = cred_def_id
        self.key_correctness_proof = key_correctness_proof


class AnonCredsLinkSecretSchema(BaseModelSchema):
    """AnonCreds Link Secret Schema."""

    class Meta:
        """AnonCredsLinkSecret schema metadata."""

        model_class = AnonCredsLinkSecret
        unknown = EXCLUDE

    nonce = fields.Str(
        required=True,
        validate=NUM_STR_WHOLE_VALIDATE,
        metadata={
            "description": "Nonce in credential abstract",
            "example": NUM_STR_WHOLE_EXAMPLE,
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

    key_correctness_proof = fields.Nested(
        IndyKeyCorrectnessProofSchema(),
        required=True,
        metadata={"description": "Key correctness proof"},
    )


class DidcommSignedAttachment(BaseModel):
    """Didcomm Signed Attachment Model."""

    class Meta:
        """DidcommSignedAttachment metadata."""

        schema_class = "DidcommSignedAttachmentSchema"

    def __init__(
        self,
        algs_supported: Sequence[str] = None,
        did_methods_supported: Sequence[str] = None,
        nonce: Optional[str] = None,
        **kwargs,
    ):
        """Initialize values for DidcommSignedAttachment."""
        super().__init__(**kwargs)
        self.algs_supported = algs_supported
        self.did_methods_supported = did_methods_supported
        self.nonce = nonce


class DidcommSignedAttachmentSchema(BaseModelSchema):
    """Didcomm Signed Attachment Schema."""

    class Meta:
        """Didcomm signed attachment schema metadata."""

        model_class = DidcommSignedAttachment
        unknown = EXCLUDE

    algs_supported = fields.List(fields.Str(), required=True)

    did_methods_supported = fields.List(fields.Str(), required=True)

    nonce = fields.Str(
        required=True,
        validate=NUM_STR_WHOLE_VALIDATE,
        metadata={
            "description": "Nonce in credential abstract",
            "example": NUM_STR_WHOLE_EXAMPLE,
        },
    )


class BindingMethod(BaseModel):
    """Binding Method Model."""

    class Meta:
        """Binding method metadata."""

        schema_class = "BindingMethodSchema"

    def __init__(
        self,
        anoncreds_link_secret: Union[dict, AnonCredsLinkSecret] = None,
        didcomm_signed_attachment: Union[dict, DidcommSignedAttachment] = None,
        **kwargs,
    ):
        """Initialize values for DidcommSignedAttachment."""
        super().__init__(**kwargs)
        self.anoncreds_link_secret = anoncreds_link_secret
        self.didcomm_signed_attachment = didcomm_signed_attachment


class BindingMethodSchema(BaseModelSchema):
    """VCDI Binding Method Schema."""

    class Meta:
        """VCDI binding method schema metadata."""

        model_class = BindingMethod
        unknown = EXCLUDE

    anoncreds_link_secret = fields.Nested(AnonCredsLinkSecretSchema, required=False)
    didcomm_signed_attachment = fields.Nested(
        DidcommSignedAttachmentSchema, required=True
    )


class VCDICredAbstract(BaseModel):
    """VCDI Credential Abstract."""

    class Meta:
        """VCDI credential abstract metadata."""

        schema_class = "VCDICredAbstractSchema"

    def __init__(
        self,
        data_model_versions_supported: Sequence[str] = None,
        binding_required: Optional[str] = None,
        binding_method: Optional[str] = None,
        credential: Union[dict, VerifiableCredential] = None,
        **kwargs,
    ):
        """Initialize vcdi cred abstract object.

        Args:
            data_model_versions_supported: supported versions for data model
            binding_required: boolean value
            binding_method: required if binding_required is true
            credential: credential object
            kwargs: additional key-value arguments to map into message class properties
        """
        super().__init__(**kwargs)
        self.data_model_versions_supported = data_model_versions_supported
        self.binding_required = binding_required
        self.binding_method = binding_method
        self.credential = credential


class VCDICredAbstractSchema(BaseModelSchema):
    """VCDI Credential Abstract Schema."""

    class Meta:
        """VCDICredAbstractSchema metadata."""

        model_class = VCDICredAbstract
        unknown = EXCLUDE

    data_model_versions_supported = fields.List(
        fields.Str(), required=True, metadata={"description": "", "example": ""}
    )

    binding_required = fields.Bool(
        required=False, metadata={"description": "", "example": ""}
    )

    binding_method = fields.Nested(
        BindingMethodSchema(),
        required=binding_required,
        metadata={"description": "", "example": ""},
    )

    credential = fields.Nested(
        CredentialSchema(),
        required=True,
        metadata={"description": "", "example": ""},
    )
