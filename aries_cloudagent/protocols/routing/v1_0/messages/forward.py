"""Represents a forward message."""

import json

from typing import Union

from marshmallow import EXCLUDE, fields, pre_load

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import FORWARD, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.forward_handler.ForwardHandler"


class Forward(AgentMessage):
    """Represents a request to forward a message to a connected agent."""

    class Meta:
        """Forward metadata."""

        handler_class = HANDLER_CLASS
        message_type = FORWARD
        schema_class = "ForwardSchema"

    def __init__(self, *, to: str = None, msg: Union[dict, str] = None, **kwargs):
        """
        Initialize forward message object.

        Args:
            to (str): Recipient DID
            msg (str): Message content
        """
        super().__init__(**kwargs)
        self.to = to
        if isinstance(msg, str):
            msg = json.loads(msg)
        self.msg = msg


class ForwardSchema(AgentMessageSchema):
    """Forward message schema used in serialization/deserialization."""

    class Meta:
        """ForwardSchema metadata."""

        model_class = Forward
        unknown = EXCLUDE

    @pre_load
    def handle_str_message(self, data, **kwargs):
        """Accept string value for msg, as produced by previous implementation."""
        if "msg" in data and isinstance(data["msg"], str):
            data["msg"] = json.loads(data["msg"])
        return data

    to = fields.Str(required=True)
    msg = fields.Dict(required=True)
