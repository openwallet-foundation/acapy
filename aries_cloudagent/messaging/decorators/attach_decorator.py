"""
A message decorator for attachments.

An attach decorator embeds content or specifies appended content.
"""


import base64
import json
import uuid

from typing import Union

from marshmallow import fields

from ..models.base import BaseModel, BaseModelSchema
from ..valid import BASE64, INDY_ISO8601_DATETIME, SHA256, UUIDFour


class AttachDecoratorData(BaseModel):
    """Attach decorator data."""

    class Meta:
        """AttachDecoratorData metadata."""

        schema_class = "AttachDecoratorDataSchema"

    def __init__(
        self,
        base64_: str = None,
        json_: str = None,
        links_: Union[list, str] = None,
        sha256_: str = None
    ):
        """
        Initialize decorator data.

        Specify content for one of:

            - `base64_`
            - `json_`
            - `links_` and optionally `sha256_`.

        Args:
            base64_: base64 encoded content for inclusion.
            json_: json-dumped content for inclusion.
            links_: list or single URL of hyperlinks.
            sha256_: sha-256 hash for URL content, if `links_` specified.

        """
        if base64_:
            self.base64_ = base64_
        elif json_:
            self.json_ = json_
        else:
            assert isinstance(links_, (str, list))
            self.links_ = [links_] if isinstance(links_, str) else list(links_)
            if sha256_:
                self.sha256_ = sha256_

    @property
    def base64(self):
        """Accessor for base64 decorator data, or None."""
        return getattr(self, "base64_", None)

    @property
    def json(self):
        """Accessor for json decorator data, or None."""
        return getattr(self, "json_", None)

    @property
    def links(self):
        """Accessor for links decorator data, or None."""
        return getattr(self, "links_", None)

    @property
    def sha256(self):
        """Accessor for sha256 decorator data, or None."""
        return getattr(self, "sha256_", None)

    def __eq__(self, other):
        """Equality comparator."""
        for attr in ["base64_", "json_", "sha256_"]:
            if getattr(self, attr, None) != getattr(other, attr, None):
                return False
        if set(getattr(self, "links_", [])) != set(getattr(other, "links_", [])):
            return False
        return True


class AttachDecoratorDataSchema(BaseModelSchema):
    """Attach decorator data schema."""

    class Meta:
        """Attach decorator data schema metadata."""

        model_class = AttachDecoratorData

    base64_ = fields.Str(
        description="Base64-encoded data",
        required=False,
        attribute="base64_",
        data_key="base64",
        **BASE64
    )
    json_ = fields.Str(
        description="JSON-serialized data",
        required=False,
        example='{"sample": "content"}',
        attribute="json_",
        data_key="json"
    )
    links_ = fields.List(
        fields.Str(example="https://link.to/data"),
        description="List of hypertext links to data",
        required=False,
        attribute="links_",
        data_key="links"
    )
    sha256_ = fields.Str(
        description="SHA256 hash of linked data",
        required=False,
        attribute="sha256_",
        data_key="sha256",
        **SHA256
    )


class AttachDecorator(BaseModel):
    """Class representing attach decorator."""

    class Meta:
        """AttachDecorator metadata."""

        schema_class = "AttachDecoratorSchema"

    def __init__(
        self,
        *,
        ident: str = None,
        description: str = None,
        filename: str = None,
        mime_type: str = None,
        lastmod_time: str = None,
        byte_count: int = None,
        data: AttachDecoratorData,
        **kwargs
    ):
        """
        Initialize an AttachDecorator instance.

        The attachment decorator allows for embedding or appending
        content to a message.

        Args:
            ident ("@id" in serialization): identifier for the appendage
            mime_type ("mime-type" in serialization): MIME type for attachment
            filename: file name
            lastmod_time: last modification time, "%Y-%m-%d %H:%M:%SZ"
            description: content description
            data: payload, as per `AttachDecoratorData`

        """
        super().__init__(**kwargs)
        self.ident = ident
        self.description = description
        self.filename = filename
        self.mime_type = mime_type
        self.lastmod_time = lastmod_time
        self.byte_count = byte_count
        self.data = data

    @property
    def indy_dict(self):
        """
        Return indy data structure encoded in attachment.

        Returns: dict with indy object in data attachment

        """
        assert hasattr(self.data, "base64_")
        return json.loads(base64.b64decode(self.data.base64_.encode()).decode())

    @classmethod
    def from_indy_dict(
        cls,
        indy_dict: dict,
        *,
        ident: str = None,
        description: str = None,
        filename: str = None,
        lastmod_time: str = None,
        byte_count: int = None,
    ):
        """
        Create `AttachDecorator` instance from indy object (dict).

        Given indy object (dict), JSON dump, base64-encode, and embed
        it as data; mark `application/json` MIME type.

        Args:
            indy_dict: indy (dict) data structure
            ident: optional attachment identifier (default random UUID4)
            description: optional attachment description
            filename: optional attachment filename
            lastmod_time: optional attachment last modification time
            byte_count: optional attachment byte count

        """
        return AttachDecorator(
            ident=ident or str(uuid.uuid4()),
            description=description,
            filename=filename,
            mime_type="application/json",
            lastmod_time=lastmod_time,
            byte_count=byte_count,
            data=AttachDecoratorData(
                base64_=base64.b64encode(json.dumps(indy_dict).encode()).decode()
            )
        )


class AttachDecoratorSchema(BaseModelSchema):
    """Attach decorator schema used in serialization/deserialization."""

    class Meta:
        """AttachDecoratorSchema metadata."""

        model_class = AttachDecorator

    ident = fields.Str(
        description="Attachment identifier",
        example=UUIDFour.EXAMPLE,
        required=False,
        allow_none=False,
        data_key="@id"
    )
    mime_type = fields.Str(
        description="MIME type",
        example="image/png",
        required=False,
        data_key="mime-type"
    )
    filename = fields.Str(
        description="File name",
        example="IMG1092348.png",
        required=False
    )
    byte_count = fields.Integer(
        description="Byte count of data included by reference",
        example=1234,
        required=False
    )
    lastmod_time = fields.Str(
        description="Hint regarding last modification datetime, in ISO-8601 format",
        required=False,
        **INDY_ISO8601_DATETIME
    )
    description = fields.Str(
        description="Human-readable description of content",
        example="view from doorway, facing east, with lights off",
        required=False
    )
    data = fields.Nested(
        AttachDecoratorDataSchema,
        required=True,
    )
