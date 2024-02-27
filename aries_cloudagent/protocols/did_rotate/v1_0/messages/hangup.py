"""Hangup message."""

from marshmallow import EXCLUDE

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from ..message_types import HANGUP, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.hangup_handler.HangupHandler"


class Hangup(AgentMessage):
    """Class representing a hangup message."""

    class Meta:
        """Hangup metadata."""

        handler_class = HANDLER_CLASS
        message_type = HANGUP
        schema_class = "HangupSchema"

    def __init__(self, **kwargs):
        """Initialize a Hangup message instance."""
        super().__init__(**kwargs)


class HangupSchema(AgentMessageSchema):
    """Schema for Hangup class."""

    class Meta:
        """HangupSchema metadata."""

        model_class = Hangup
        unknown = EXCLUDE
