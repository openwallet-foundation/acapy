"""Credential preview inner object."""

from typing import Sequence, Mapping

from marshmallow import EXCLUDE, fields, ValidationError, pre_load, post_dump

from ......messaging.models.base import BaseModel, BaseModelSchema
from ......wallet.util import b64_to_str

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import CRED_20_PREVIEW


class V20CredAttrSpec(BaseModel):
    """Attribute preview."""

    class Meta:
        """Attribute preview metadata."""

        schema_class = "V20CredAttrSpecSchema"

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
    def list_plain(plain: dict) -> Sequence["V20CredAttrSpec"]:
        """
        Return a list of `V20CredAttrSpec` (copies), absent any MIME types.

        Args:
            plain: dict mapping names to values

        Returns:
            List of `V20CredAttrSpec` (copies), absent any MIME types

        """
        return [V20CredAttrSpec(name=k, value=plain[k]) for k in plain]

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


class V20CredAttrSpecSchema(BaseModelSchema):
    """Attribute preview schema."""

    class Meta:
        """Attribute preview schema metadata."""

        model_class = V20CredAttrSpec
        unknown = EXCLUDE

    name = fields.Str(
        description="Attribute name", required=True, example="favourite_drink"
    )
    mime_type = fields.Str(
        description="MIME type: omit for (null) default",
        required=False,
        data_key="mime-type",
        example="image/jpeg",
        allow_none=True,
    )
    value = fields.Str(
        description="Attribute value: base64-encode if MIME type is present",
        required=True,
        example="martini",
    )


class V20CredPreview(BaseModel):
    """Credential preview."""

    class Meta:
        """Credential preview metadata."""

        schema_class = "V20CredPreviewSchema"
        message_type = CRED_20_PREVIEW

    def __init__(
        self,
        *,
        _type: str = None,
        attributes: Sequence[V20CredAttrSpec] = None,
        attributes_dict: Mapping = None,
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
        self.attributes = list(attributes) if attributes else []
        self.attributes_dict = attributes_dict

    @property
    def _type(self):
        """Accessor for message type."""
        return DIDCommPrefix.qualify_current(V20CredPreview.Meta.message_type)

    def attr_dict(self, decode: bool = False, attach_id: str = None):
        """
        Return name:value pair per attribute.

        Args:
            decode: whether first to decode attributes with MIME type

        """
        if attach_id:
            return {
                attr.name: b64_to_str(attr.value)
                if attr.mime_type and decode
                else attr.value
                for attr in self.attributes_dict.get(attach_id)
            }
        else:
            return {
                attr.name: b64_to_str(attr.value)
                if attr.mime_type and decode
                else attr.value
                for attr in self.attributes
            }

    def mime_types(self, attach_id: str = None):
        """
        Return per-attribute mapping from name to MIME type.

        Return empty dict if no attribute has MIME type.

        """
        if attach_id:
            return {
                attr.name: attr.mime_type
                for attr in self.attributes_dict.get(attach_id)
                if attr.mime_type
            }
        else:
            return {
                attr.name: attr.mime_type for attr in self.attributes if attr.mime_type
            }


class V20CredPreviewSchema(BaseModelSchema):
    """Credential preview schema."""

    class Meta:
        """Credential preview schema metadata."""

        model_class = V20CredPreview
        unknown = EXCLUDE

    _type = fields.Str(
        description="Message type identifier",
        required=False,
        example=CRED_20_PREVIEW,
        data_key="@type",
    )
    attributes = fields.Nested(
        V20CredAttrSpecSchema, many=True, required=False, data_key="attributes"
    )
    attributes_dict = fields.Dict(
        keys=fields.Str(description="identifier"),
        values=fields.Nested(V20CredAttrSpecSchema, many=True, required=True),
        required=False,
    )

    def check_cred_ident_in_keys(self, attr_dict):
        """Check for indy or ld_proof in attachment identifier."""
        for key, value in attr_dict.items():
            if "indy" in key or "ld_proof" in key:
                return True
        return False

    @pre_load
    def extract_and_process_attributes(self, data, **kwargs):
        """Process attributes and populate attributes_dict accordingly."""
        if not data.get("attributes") and not data.get("attributes_dict"):
            raise ValidationError("Missing attributes dict")
        elif data.get("attributes") and data.get("attributes_dict"):
            raise ValidationError("Only specify either attributes or attributes_dict")
        elif data.get("attributes") and not data.get("attributes_dict"):
            attr_data = data.get("attributes")
            if isinstance(attr_data, dict) and self.check_cred_ident_in_keys(attr_data):
                data["attributes_dict"] = attr_data
                del data["attributes"]
        return data

    @post_dump
    def cleanup_attributes(self, data, **kwargs):
        """Cleanup attributes_dict and return as attributes."""
        if data.get("attributes_dict"):
            data["attributes"] = data.get("attributes_dict")
            del data["attributes_dict"]
        return data
