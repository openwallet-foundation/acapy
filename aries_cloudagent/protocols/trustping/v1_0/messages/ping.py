"""Represents a trust ping message."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

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
        super().__init__(**kwargs)
        self.comment = comment
        self.response_requested = response_requested


class PingSchema(AgentMessageSchema):
    """Schema for Ping class."""

    class Meta:
        """PingSchema metadata."""

        model_class = Ping
        unknown = EXCLUDE

    response_requested = fields.Bool(
        description="Whether response is requested (default True)",
        default=True,
        required=False,
        example=True,
    )
    comment = fields.Str(
        description="Optional comment to include",
        required=False,
        allow_none=True,
        example="Hello",
    )
