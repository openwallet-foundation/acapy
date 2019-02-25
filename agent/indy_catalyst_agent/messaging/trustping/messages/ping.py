"""Represents a trust ping message."""

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import PING

HANDLER_CLASS = (
    "indy_catalyst_agent.messaging.trustping." + "handlers.ping_handler.PingHandler"
)


class Ping(AgentMessage):
    """Class representing a trustping message."""

    class Meta:
        """Ping metadata."""

        handler_class = HANDLER_CLASS
        message_type = PING
        schema_class = "PingSchema"


class PingSchema(AgentMessageSchema):
    """Schema for Ping class."""

    class Meta:
        """PingSchema metadata."""

        model_class = Ping
