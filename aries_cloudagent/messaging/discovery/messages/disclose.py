"""Represents a protocol discovery disclosure message."""

from typing import Mapping

from marshmallow import fields, Schema

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import DISCLOSE

HANDLER_CLASS = (
    "aries_cloudagent.messaging.discovery.handlers.disclose_handler.DiscloseHandler"
)


class Disclose(AgentMessage):
    """Represents a protocol discovery disclosure, the response to a query message."""

    class Meta:
        """Disclose metadata."""

        handler_class = HANDLER_CLASS
        message_type = DISCLOSE
        schema_class = "DiscloseSchema"

    def __init__(self, *, protocols: Mapping[str, Mapping] = None, **kwargs):
        """
        Initialize disclose message object.

        Args:
            protocols: A mapping of protocol names to a dictionary of properties
        """
        super(Disclose, self).__init__(**kwargs)
        self.protocols = list(protocols) if protocols else []


class ProtocolDescriptorSchema(Schema):
    """Schema for an entry in the protocols list."""

    pid = fields.Str(required=True)
    roles = fields.List(fields.Str(), required=False, allow_none=True)


class DiscloseSchema(AgentMessageSchema):
    """Disclose message schema used in serialization/deserialization."""

    class Meta:
        """DiscloseSchema metadata."""

        model_class = Disclose

    protocols = fields.List(fields.Nested(ProtocolDescriptorSchema()), required=True)
