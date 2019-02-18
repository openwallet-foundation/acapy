"""
Represents a trust ping message
"""

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import PING

HANDLER_CLASS = (
    "indy_catalyst_agent.messaging.trustping."
    + "handlers.ping_handler.PingHandler"
)


class Ping(AgentMessage):
    class Meta:
        handler_class = HANDLER_CLASS
        message_type = PING
        schema_class = "PingSchema"


class PingSchema(AgentMessageSchema):
    class Meta:
        model_class = Ping
