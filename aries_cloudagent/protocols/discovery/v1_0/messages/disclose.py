"""Represents a feature discovery disclosure message."""

from typing import Mapping, Sequence

from marshmallow import EXCLUDE, fields, Schema

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import DISCLOSE, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.disclose_handler.DiscloseHandler"


class Disclose(AgentMessage):
    """Represents a feature discovery disclosure, the response to a query message."""

    class Meta:
        """Disclose metadata."""

        handler_class = HANDLER_CLASS
        message_type = DISCLOSE
        schema_class = "DiscloseSchema"

    def __init__(self, *, protocols: Sequence[Mapping[str, Mapping]] = None, **kwargs):
        """
        Initialize disclose message object.

        Args:
            protocols: A mapping of protocol names to a dictionary of properties
        """
        super().__init__(**kwargs)
        self.protocols = list(protocols) if protocols else []


class ProtocolDescriptorSchema(Schema):
    """Schema for an entry in the protocols list."""

    pid = fields.Str(required=True)
    roles = fields.List(
        fields.Str(
            description="Role: requester or responder",
            example="requester",
        ),
        required=False,
        allow_none=True,
        description="List of roles",
    )


class DiscloseSchema(AgentMessageSchema):
    """Disclose message schema used in serialization/deserialization."""

    class Meta:
        """DiscloseSchema metadata."""

        model_class = Disclose
        unknown = EXCLUDE

    protocols = fields.List(
        fields.Nested(ProtocolDescriptorSchema()),
        required=True,
        description="List of protocol descriptors",
    )
