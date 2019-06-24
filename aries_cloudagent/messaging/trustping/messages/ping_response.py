"""Represents an response to a trust ping message."""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import PING_RESPONSE

HANDLER_CLASS = (
    "aries_cloudagent.messaging.trustping."
    + "handlers.ping_response_handler.PingResponseHandler"
)


class PingResponse(AgentMessage):
    """Class representing a ping response."""

    class Meta:
        """PingResponse metadata."""

        handler_class = HANDLER_CLASS
        message_type = PING_RESPONSE
        schema_class = "PingResponseSchema"

    def __init__(self, *, comment: str = None, **kwargs):
        """
        Initialize a PingResponse message instance.

        Args:
            comment: An optional comment string to include in the message

        """
        super(PingResponse, self).__init__(**kwargs)
        self.comment = comment


class PingResponseSchema(AgentMessageSchema):
    """PingResponse schema."""

    class Meta:
        """PingResponseSchema metadata."""

        model_class = PingResponse

    comment = fields.Str(required=False, allow_none=True)
