"""
A message decorator for attachments.

An attach decorator embeds content or specifies appended content.
"""


import base64
import json

from datetime import datetime
from typing import Mapping

from marshmallow import fields

from ..models.base import BaseModel, BaseModelSchema


class AttachDecorator(BaseModel):
    """Class representing attach decorator."""

    class Meta:
        """AttachDecorator metadata."""

        schema_class = "AttachDecoratorSchema"

    def __init__(
        self,
        *,
        append_id: str = None,
        mime_type: str = None,
        filename: str = None,
        byte_count: int = None,
        lastmod_time: datetime = None,
        description: str = None,
        data: Mapping
    ):
        """
        Initialize an AttachDecorator instance.

        The attachment decorator allows for embedding or appending
        content to a message.

        Args:
            append_id ("@id" in serialization): if appending,
                identifier for the appendage
            mime_type ("mime-type" in serialization): MIME type for attachment
            filename: file name
            lastmod_time: last modification time, '%Y-%m-%d %H:%M:%SZ'
            description: content description
            data: mapping from content format (base64, json, or links)
                to encoded content, with optional sha-256 binhex digest for
                linked content; e.g.,
                {
                    "sha256": "e91c254ad58860a02c788dfb5c1a65d6a88...",
                    "links": ["...", "..."]
                };
                e.g.,
                {
                    "base64": "..."
                }
                NOTE: At present, the implementation supports only base64 on indy.

        """
        super(AttachDecorator, self).__init__()
        self.append_id = append_id
        self.mime_type = mime_type
        self.filename = filename
        self.byte_count = byte_count
        self.lastmod_time = lastmod_time
        self.description = description
        self.data = dict(data) if data else {}

    @property
    def indy_dict(self):
        """
        Return indy data structure encoded in attachment.

        Returns: dict with indy object in data attachment

        """
        return json.loads(base64.b64decode(self.data["base64"].encode()).decode())

    @classmethod
    def from_indy_dict(cls, indy_dict: dict):
        """
        Create `AttachDecorator` instance from indy object (dict).

        Given indy object (dict), JSON dump, base64-encode, and embed
        it as data; mark `application/json` MIME type.

        Args:
            indy_dict: indy (dict) data structure
        """
        return AttachDecorator(
            mime_type="application/json",
            data={
                "base64": base64.b64encode(json.dumps(indy_dict).encode()).decode()
            }
        )


class AttachDecoratorSchema(BaseModelSchema):
    """Attach decorator schema used in serialization/deserialization."""

    class Meta:
        """AttachDecoratorSchema metadata."""

        model_class = AttachDecorator

    append_id = fields.Str(
        required=False,
        allow_none=False,
        attribute="append_id",
        data_key="@id"
    )
    mime_type = fields.Str(required=False, allow_none=False, data_key="mime-type")
    filename = fields.Str(required=False, allow_none=False)
    byte_count = fields.Integer(required=False, allow_none=False)
    lastmod_time = fields.DateTime(
        format="%Y-%m-%d %H:%M:%SZ",
        required=False,
        allow_none=False
    )
    description = fields.Str(required=False, allow_none=False)
    data = fields.Dict(required=True, allow_none=False)
