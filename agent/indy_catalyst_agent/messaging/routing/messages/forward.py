"""Represents a forward message."""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ...message_types import MessageTypes


class Forward(AgentMessage):
    """Class representing a forward message."""

    class Meta:
        """Forward metadata."""

        # handler_class = ForwardHandler
        message_type = MessageTypes.FORWARD.value
        schema_class = "ForwardSchema"

    def __init__(self, to: str = None, msg: str = None, **kwargs):
        """
        Initialize forward message object.

        Args:
            to (str): Recipient DID
            msg (str): Message content
        """
        super(Forward, self).__init__(**kwargs)
        self.to = to
        self.msg = msg


class ForwardSchema(AgentMessageSchema):
    """Forward schema."""

    class Meta:
        """ForwardSchema metadata."""

        model_class = Forward

    to = fields.Str(required=True)
    msg = fields.Str(required=True)
