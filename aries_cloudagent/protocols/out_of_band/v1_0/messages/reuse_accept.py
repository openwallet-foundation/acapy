"""Represents a Handshake Reuse Accept message under RFC 0434."""

from marshmallow import EXCLUDE, pre_dump, ValidationError

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import MESSAGE_REUSE_ACCEPT, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers"
    ".reuse_accept_handler.HandshakeReuseAcceptMessageHandler"
)


class HandshakeReuseAccept(AgentMessage):
    """Class representing a Handshake Reuse Accept message."""

    class Meta:
        """Metadata for Handshake Reuse Accept message."""

        handler_class = HANDLER_CLASS
        message_type = MESSAGE_REUSE_ACCEPT
        schema_class = "HandshakeReuseAcceptSchema"

    def __init__(
        self,
        **kwargs,
    ):
        """Initialize Handshake Reuse Accept object."""
        super().__init__(**kwargs)


class HandshakeReuseAcceptSchema(AgentMessageSchema):
    """Handshake Reuse Accept schema class."""

    class Meta:
        """Handshake Reuse Accept schema metadata."""

        model_class = HandshakeReuseAccept
        unknown = EXCLUDE

    @pre_dump
    def check_thread_deco(self, obj, **kwargs):
        """Thread decorator, and its thid and pthid, are mandatory."""
        if not obj._decorators.to_dict().get("~thread", {}).keys() >= {"thid", "pthid"}:
            raise ValidationError("Missing required field(s) in thread decorator")
        return obj
