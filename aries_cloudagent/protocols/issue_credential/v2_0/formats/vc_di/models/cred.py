"""Cred request artifacts to attach to RFC 453 messages."""

from aries_cloudagent.messaging.models.base import BaseModel, BaseModelSchema
from marshmallow import EXCLUDE, fields


class VCDIIndyCredential(BaseModel):
    """VCDI Indy credential."""

    class Meta:
        """VCDI Indy credential metadata."""

        schema_class = "VCDIIndyCredentialSchema"

    def __init__(
        self,
        credential: dict = None,
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
        self.credential = credential


class VCDIIndyCredentialSchema(BaseModelSchema):
    """VCDI Indy credential schema."""

    class Meta:
        """VCDI Indy credential schemametadata."""

        model_class = VCDIIndyCredential
        unknown = EXCLUDE

    credential = fields.Dict(
        fields.Str(), required=True, metadata={"description": "", "example": ""}
    )
