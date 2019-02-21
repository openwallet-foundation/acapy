"""
Represents an response to a trust ping message
"""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import PING_RESPONSE

HANDLER_CLASS = (
    "indy_catalyst_agent.messaging.trustping."
    + "handlers.ping_response_handler.PingResponseHandler"
)


class PingResponse(AgentMessage):
    class Meta:
        handler_class = HANDLER_CLASS
        message_type = PING_RESPONSE
        schema_class = "PingResponseSchema"

    def __init__(self, *, comment: str = None, **kwargs):
        super(PingResponse, self).__init__(**kwargs)
        self.comment = comment


class PingResponseSchema(AgentMessageSchema):
    class Meta:
        model_class = PingResponse

    comment = fields.Str(required=False, allow_none=True)
