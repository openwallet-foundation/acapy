"""Credential preview inner object."""

from typing import Sequence

from marshmallow import EXCLUDE, fields

from ......messaging.models.base import BaseModel, BaseModelSchema
from ......wallet.util import b64_to_str

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import CRED_30_PREVIEW


class V30CredAttrSpec(BaseModel):
    """Attribute preview."""

    class Meta:
        """Attribute preview metadata."""

        schema_class = "V30CredAttrSpecSchema"

    def __init__(self, *, name: str, value: str, mime_type: str = None, **kwargs):
        """
        Initialize attribute preview object.

        Args:
            name: attribute name
            value: attribute value; caller must base64-encode for attributes with
                non-empty MIME type
            mime_type: MIME type (default null)

        """
        super().__init__(**kwargs)

        self.name = name
        self.value = value
        self.mime_type = mime_type.lower() if mime_type else None

    @staticmethod
    def list_plain(plain: dict) -> Sequence["V30CredAttrSpec"]:
        """
        Return a list of `V30CredAttrSpec` (copies), absent any MIME types.

        Args:
            plain: dict mapping names to values

        Returns:
            List of `V30CredAttrSpec` (copies), absent any MIME types

        """
        return [V30CredAttrSpec(name=k, value=plain[k]) for k in plain]

    def b64_decoded_value(self) -> str:
        """Value, base64-decoded if applicable."""

        return b64_to_str(self.value) if self.value and self.mime_type else self.value

    def __eq__(self, other):
        """Equality comparator."""

        if self.name != other.name:
            return False  # distinct attribute names

        if self.mime_type != other.mime_type:
            return False  # distinct MIME types

        return self.b64_decoded_value() == other.b64_decoded_value()


class V30CredAttrSpecSchema(BaseModelSchema):
    """Attribute preview schema."""

    class Meta:
        """Attribute preview schema metadata."""

        model_class = V30CredAttrSpec
        unknown = EXCLUDE

    name = fields.Str(
        description="Attribute name", required=True, example="favourite_drink"
    )
    mime_type = fields.Str(
        description="MEDIA type: omit for (null) default",
        required=False,
        data_key="media-type",
        example="image/jpeg",
        allow_none=True,
    )
    value = fields.Str(
        description="Attribute value: base64-encode if MIME type is present",
        required=True,
        example="martini",
    )


class V30CredPreviewBody(BaseModel):
    """Issue credential Cred Preview Body."""

    class Meta:
        """Issue credential Cred Preview Body metadata."""

        schema_class = "V30CredPreviewBodySchema"

    def __init__(
        self,
        attributes: Sequence[V30CredAttrSpec] = None,
        **kwargs,
    ):
        """
        Initialize attribute preview object.

         Args:
        attributes

        """
        super().__init__(**kwargs)

        self.attributes = list(attributes) if attributes else []

    @property
    def _type(self):
        """Accessor for message type."""
        return DIDCommPrefix.qualify_current(V30CredPreview.Meta.message_type)

    def attr_dict(self, decode: bool = False):
        """
        Return name:value pair per attribute.

        Args:
            decode: whether first to decode attributes with MIME type

        """

        return {
            attr.name: b64_to_str(attr.value)
            if attr.mime_type and decode
            else attr.value
            for attr in self.attributes
        }

    def mime_types(self):
        """
        Return per-attribute mapping from name to MIME type.

        Return empty dict if no attribute has MIME type.

        """
        return {attr.name: attr.mime_type for attr in self.attributes if attr.mime_type}


class V30CredPreview(BaseModel):
    """Credential preview."""

    class Meta:
        """Credential preview metadata."""

        schema_class = "V30CredPreviewSchema"
        message_type = CRED_30_PREVIEW

    def __init__(
        self,
        *,
        type: str = CRED_30_PREVIEW,
        _body: V30CredPreviewBody = None,
        **kwargs,
    ):
        """
        Initialize credential preview object.

        Args:
            _type: formalism for Marshmallow model creation: ignored
            attributes (list): list of attribute preview dicts; e.g., [
                {
                    "name": "attribute_name",
                    "value": "value"
                },
                {
                    "name": "icon",
                    "mime-type": "image/png",
                    "value": "cG90YXRv"
                },
            ]

        """
        super().__init__(**kwargs)
        self.type = type
        self._body = _body


class V30CredPreviewBodySchema(BaseModelSchema):
    """Credential body prewview schema."""

    class Meta:
        """Credential body prewview schema."""

        model_class = V30CredPreviewBody
        unknown = EXCLUDE

    attributes = fields.Nested(
        V30CredAttrSpecSchema, many=True, required=False, data_key="attributes"
    )


class V30CredPreviewSchema(BaseModelSchema):
    """Credential preview schema."""

    class Meta:
        """Credential preview schema metadata."""

        model_class = V30CredPreview
        unknown = EXCLUDE

    type = fields.Str(
        description="Message type identifier",
        required=False,
        example=CRED_30_PREVIEW,
        data_key="type",
        allow_none=False,
    )
    _body = fields.Nested(
        V30CredPreviewBodySchema, required=True, allow_none=False, data_key="body"
    )
