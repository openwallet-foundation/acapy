"""Cred request artifacts to attach to RFC 453 messages."""

from typing import Optional

from marshmallow import EXCLUDE, fields

from .......messaging.models.base import BaseModel, BaseModelSchema


class VCDIIndyCredential(BaseModel):
    """VCDI Indy credential."""

    class Meta:
        """VCDI Indy credential metadata."""

        schema_class = "VCDIIndyCredentialSchema"

    def __init__(
        self,
        credential: Optional[dict] = None,
        **kwargs,
    ):
        """Initialize vcdi cred abstract object.

        Args:
            credential: credential object
            kwargs: additional keyword arguments
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
