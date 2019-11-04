"""Represents a forward message."""

from marshmallow import fields

from ....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import FORWARD, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.forward_handler.ForwardHandler"


class Forward(AgentMessage):
    """Represents a request to forward a message to a connected agent."""

    class Meta:
        """Forward metadata."""

        handler_class = HANDLER_CLASS
        message_type = FORWARD
        schema_class = "ForwardSchema"

    def __init__(self, *, to: str = None, msg: str = None, **kwargs):
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
    """Forward message schema used in serialization/deserialization."""

    class Meta:
        """ForwardSchema metadata."""

        model_class = Forward

    to = fields.Str(required=True)
    msg = fields.Str(required=True)
