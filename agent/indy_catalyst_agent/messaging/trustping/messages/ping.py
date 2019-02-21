"""
Represents a trust ping message
"""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import PING

HANDLER_CLASS = (
    "indy_catalyst_agent.messaging.trustping." + "handlers.ping_handler.PingHandler"
)


class Ping(AgentMessage):
    class Meta:
        handler_class = HANDLER_CLASS
        message_type = PING
        schema_class = "PingSchema"

    def __init__(
        self, *, response_requested: bool = None, comment: str = None, **kwargs
    ):
        super(Ping, self).__init__(**kwargs)
        self.comment = comment
        self.response_requested = response_requested


class PingSchema(AgentMessageSchema):
    class Meta:
        model_class = Ping

    response_requested = fields.Bool(default=True, required=False)
    comment = fields.Str(required=False, allow_none=True)
