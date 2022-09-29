"""Represents a Handshake Reuse message under RFC 0434."""

from marshmallow import EXCLUDE, pre_dump, ValidationError
from string import Template

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import MESSAGE_REUSE, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.reuse_handler.HandshakeReuseMessageHandler"
)
BASE_PROTO_VERSION = "1.0"


class HandshakeReuse(AgentMessage):
    """Class representing a Handshake Reuse message."""

    class Meta:
        """Metadata for Handshake Reuse message."""

        handler_class = HANDLER_CLASS
        message_type = MESSAGE_REUSE
        schema_class = "HandshakeReuseSchema"

    def __init__(
        self,
        version: str = BASE_PROTO_VERSION,
        **kwargs,
    ):
        """Initialize Handshake Reuse message object."""
        super().__init__(**kwargs)
        self.assign_version_to_message_type(version=version)

    @classmethod
    def assign_version_to_message_type(cls, version: str):
        """Assign version to Meta.message_type."""
        cls.Meta.message_type = Template(cls.Meta.message_type).substitute(
            version=version
        )


class HandshakeReuseSchema(AgentMessageSchema):
    """Handshake Reuse schema class."""

    class Meta:
        """Handshake Reuse schema metadata."""

        model_class = HandshakeReuse
        unknown = EXCLUDE

    @pre_dump
    def check_thread_deco(self, obj, **kwargs):
        """Thread decorator, and its thid and pthid, are mandatory."""
        if not obj._decorators.to_dict().get("~thread", {}).keys() >= {"thid", "pthid"}:
            raise ValidationError("Missing required field(s) in thread decorator")
        return obj
