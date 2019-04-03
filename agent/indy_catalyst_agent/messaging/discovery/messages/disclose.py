"""Represents a protocol discovery disclosure message."""

from typing import Mapping

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import DISCLOSE

HANDLER_CLASS = "indy_catalyst_agent.messaging.discovery.handlers"
".disclose_handler.DiscloseHandler"


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
        self.protocols = protocols or {}


class DiscloseSchema(AgentMessageSchema):
    """Disclose message schema used in serialization/deserialization."""

    class Meta:
        """DiscloseSchema metadata."""

        model_class = Disclose

    protocols = fields.Dict(fields.Str(), fields.Dict(fields.Str()), required=True)
