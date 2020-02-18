"""Represents a trust ping message."""

from marshmallow import fields

from ....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import PING, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.ping_handler.PingHandler"


class Ping(AgentMessage):
    """Class representing a trustping message."""

    class Meta:
        """Ping metadata."""

        handler_class = HANDLER_CLASS
        message_type = PING
        schema_class = "PingSchema"

    def __init__(
        self, *, response_requested: bool = True, comment: str = None, **kwargs
    ):
        """
        Initialize a Ping message instance.

        Args:
            response_requested: A flag indicating that a response is requested
                (defaults to True for the recipient if not included)
            comment: An optional comment string

        """
        super(Ping, self).__init__(**kwargs)
        self.comment = comment
        self.response_requested = response_requested


class PingSchema(AgentMessageSchema):
    """Schema for Ping class."""

    class Meta:
        """PingSchema metadata."""

        model_class = Ping

    response_requested = fields.Bool(
        default=True,
        required=False,
        description="Whether response is requested (default True)",
        example=True,
    )
    comment = fields.Str(
        required=False,
        description="Optional comment to include",
        example="Hello",
        allow_none=True,
    )
