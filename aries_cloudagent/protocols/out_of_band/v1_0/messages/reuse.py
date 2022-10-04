"""Represents a Handshake Reuse message under RFC 0434."""

from marshmallow import EXCLUDE, fields, pre_dump, ValidationError
from typing import Optional, Text

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import MESSAGE_REUSE, PROTOCOL_PACKAGE, DEFAULT_VERSION

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.reuse_handler.HandshakeReuseMessageHandler"
)


class HandshakeReuse(AgentMessage):
    """Class representing a Handshake Reuse message."""

    class Meta:
        """Metadata for Handshake Reuse message."""

        handler_class = HANDLER_CLASS
        message_type = MESSAGE_REUSE
        schema_class = "HandshakeReuseSchema"

    def __init__(
        self,
        version: str = DEFAULT_VERSION,
        msg_type: Optional[Text] = None,
        **kwargs,
    ):
        """Initialize Handshake Reuse message object."""
        super().__init__(_type=msg_type, _version=version, **kwargs)


class HandshakeReuseSchema(AgentMessageSchema):
    """Handshake Reuse schema class."""

    class Meta:
        """Handshake Reuse schema metadata."""

        model_class = HandshakeReuse
        unknown = EXCLUDE

    _type = fields.Str(
        data_key="@type",
        required=False,
        description="Message type",
        example="https://didcomm.org/my-family/1.0/my-message-type",
    )

    @pre_dump
    def check_thread_deco(self, obj, **kwargs):
        """Thread decorator, and its thid and pthid, are mandatory."""
        if not obj._decorators.to_dict().get("~thread", {}).keys() >= {"thid", "pthid"}:
            raise ValidationError("Missing required field(s) in thread decorator")
        return obj
