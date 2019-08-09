"""A credential preview inner object."""


from typing import Sequence

import base64

from marshmallow import fields, validate

from .....models.base import BaseModel, BaseModelSchema
from ...message_types import CREDENTIAL_PREVIEW


class CredentialAttrPreview(BaseModel):
    """Class representing a preview of an attibute."""

    DEFAULT_META = {"mime-type": "text/plain"}

    class Meta:
        """Attribute preview metadata."""

        schema_class = "CredentialAttrPreviewSchema"

    def __init__(
            self,
            *,
            name: str,
            value: str,
            encoding: str = None,
            mime_type: str = None,
            **kwargs):
        """
        Initialize attribute preview object.

        Args:
            name: attribute name
            value: attribute value
            encoding: encoding (omit or "base64")
            mime_type: MIME type

        """
        super().__init__(**kwargs)
        self.name = name
        self.value = value
        self.encoding = encoding.lower() if encoding else None
        self.mime_type = (
            mime_type.lower()
            if mime_type and mime_type != CredentialAttrPreview.DEFAULT_META.get(
                "mime-type"
            )
            else None
        )

    @staticmethod
    def list_plain(plain: dict):
        """
        Return a list of `CredentialAttrPreview` for plain text from names/values.

        Args:
            plain: dict mapping names to values

        Returns:
            CredentialAttrPreview on name/values pairs with default MIME type

        """
        return [CredentialAttrPreview(name=k, value=plain[k]) for k in plain]

    def b64_decoded_value(self) -> str:
        """Value, base64-decoded if applicable."""

        return base64.b64decode(self.value.encode()).decode(
        ) if (
            self.value and
            self.encoding and
            self.encoding.lower() == "base64"
        ) else self.value

    def __eq__(self, other):
        """Equality comparator."""

        if all(
            getattr(self, attr, CredentialAttrPreview.DEFAULT_META.get(attr)) ==
            getattr(other, attr, CredentialAttrPreview.DEFAULT_META.get(attr))
            for attr in vars(self)
        ):
            return True  # all attrs exactly match

        if self.name != other.name:
            return False  # distinct attribute names

        if (
            self.mime_type or "text/plain"
        ).lower() != (other.mime_type or "text/plain").lower():
            return False  # distinct MIME types

        return self.b64_decoded_value() == other.b64_decoded_value()


class CredentialAttrPreviewSchema(BaseModelSchema):
    """Attribute preview schema."""

    class Meta:
        """Attribute preview schema metadata."""

        model_class = CredentialAttrPreview

    name = fields.Str(description="Attribute name", required=True, example="attr_name")
    mime_type = fields.Str(
        description="MIME type",
        required=False,
        data_key="mime-type",
        example="text/plain"
    )
    encoding = fields.Str(
        description="Encoding (specify base64 or omit for none)",
        required=False,
        example="base64",
        validate=validate.Equal("base64", error="Must be absent or equal to {other}")
    )
    value = fields.Str(
        description="Attribute value",
        required=True,
        example="attr_value"
    )


class CredentialPreview(BaseModel):
    """Class representing a credential preview inner object."""

    class Meta:
        """Credential preview metadata."""

        schema_class = "CredentialPreviewSchema"
        message_type = CREDENTIAL_PREVIEW

    def __init__(
            self,
            *,
            _type: str = None,
            attributes: Sequence[CredentialAttrPreview] = None,
            **kwargs):
        """
        Initialize credential preview object.

        Args:
            _type: formalism for Marshmallow model creation: ignored
            attributes (list): list of attribute preview dicts; e.g., [
                {
                    "name": "attribute_name",
                    "mime-type": "text/plain",
                    "value": "value"
                },
                {
                    "name": "icon",
                    "mime-type": "image/png",
                    "encoding": "base64",
                    "value": "cG90YXRv"
                }
            ]

        """
        super().__init__(**kwargs)
        self.attributes = list(attributes) if attributes else []

    @property
    def _type(self):
        """Accessor for message type."""
        return CredentialPreview.Meta.message_type

    def attr_dict(self, decode: bool = False):
        """
        Return name:value pair per attribute.

        Args:
            decode: whether first to decode attributes marked as having encoding

        """
        return {
            attr.name: base64.b64decode(attr.value.encode()).decode()
            if (
                attr.encoding
                and attr.encoding.lower() == "base64"
                and decode
            ) else attr.value
            for attr in self.attributes
        }

    def metadata(self):
        """Return per-attribute mapping from name to MIME type and encoding."""
        return {
            attr.name: {
                **{"mime-type": attr.mime_type for attr in [attr] if attr.mime_type},
                **{"encoding": attr.encoding for attr in [attr] if attr.encoding}
            } for attr in self.attributes
        }


class CredentialPreviewSchema(BaseModelSchema):
    """Credential preview schema."""

    class Meta:
        """Credential preview schema metadata."""

        model_class = CredentialPreview

    _type = fields.Str(
        description="Message type identifier",
        required=False,
        example=CREDENTIAL_PREVIEW,
        data_key="@type",
        validate=validate.Equal(
            CREDENTIAL_PREVIEW,
            error="Must be absent or equal to {other}"
        )
    )
    attributes = fields.Nested(
        CredentialAttrPreviewSchema,
        many=True,
        required=True,
        data_key="attributes"
    )
