"""Cred abstract artifacts to attach to RFC 453 messages."""

from typing import Sequence, Union
from ...vc.vc_ld.models.credential import CredentialSchema, VerifiableCredential

from marshmallow import EXCLUDE, fields

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.valid import (
    INDY_CRED_DEF_ID_EXAMPLE,
    INDY_CRED_DEF_ID_VALIDATE,
    INDY_SCHEMA_ID_EXAMPLE,
    INDY_SCHEMA_ID_VALIDATE,
    NUM_STR_WHOLE_EXAMPLE,
    NUM_STR_WHOLE_VALIDATE,
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
        """Initialize indy cred abstract object.

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
        validate=INDY_SCHEMA_ID_VALIDATE,
        metadata={
            "description": "Schema identifier",
            "example": INDY_SCHEMA_ID_EXAMPLE,
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
    nonce = fields.Str(
        required=True,
        validate=NUM_STR_WHOLE_VALIDATE,
        metadata={
            "description": "Nonce in credential abstract",
            "example": NUM_STR_WHOLE_EXAMPLE,
        },
    )
    key_correctness_proof = fields.Nested(
        IndyKeyCorrectnessProofSchema(),
        required=True,
        metadata={"description": "Key correctness proof"},
    )


class AnoncredsLinkSecret(BaseModel):
    """Anoncreds Link Secret Model."""

    class Meta:
        """AnoncredsLinkSecret metadata."""

        schema_class = "AnoncredsLinkSecretSchema"

    def __init__(
        self,
        nonce: str = None,
        cred_def_id: str = None,
        key_correctness_proof: str = None,
        **kwargs,
    ):
        """Initialize values for AnoncredsLinkSecret."""
        super().__init__(**kwargs)
        self.nonce = nonce
        self.cred_def_id = cred_def_id
        self.key_correctness_proof = key_correctness_proof


class AnoncredsLinkSecretSchema(BaseModelSchema):
    """Anoncreds Link Secret Schema."""

    class Meta:
        """AnoncredsLinkSecret schema metadata."""

        model_class = AnoncredsLinkSecret
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
        nonce: str = None,
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
        anoncreds_link_secret: Union[dict, AnoncredsLinkSecret] = None,
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

    anoncreds_link_secret = fields.Nested(AnoncredsLinkSecretSchema, required=False)
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
        binding_required: str = None,
        binding_method: str = None,
        credential: Union[dict, VerifiableCredential] = None,
        **kwargs,
    ):
        """Initialize vcdi cred abstract object.

        Args:
            data_model_versions_supported: supported versions for data model
            binding_required: boolean value
            binding_methods: required if binding_required is true
            credential: credential object
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
