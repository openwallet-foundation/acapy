"""Represents an response to a trust ping message."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from ..message_types import PING_RESPONSE, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.ping_response_handler.PingResponseHandler"


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
        super().__init__(**kwargs)
        self.comment = comment


class PingResponseSchema(AgentMessageSchema):
    """PingResponse schema."""

    class Meta:
        """PingResponseSchema metadata."""

        model_class = PingResponse
        unknown = EXCLUDE

    comment = fields.Str(
        required=False,
        allow_none=True,
        metadata={"description": "Optional comment to include", "example": "Hello"},
    )
