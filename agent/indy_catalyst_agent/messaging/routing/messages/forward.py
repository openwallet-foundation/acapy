"""
Represents a forward message.
"""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ...message_types import MessageTypes


class Forward(AgentMessage):
    class Meta:
        # handler_class = ForwardHandler
        message_type = MessageTypes.FORWARD.value
        schema_class = 'ForwardSchema'

    def __init__(self, to: str = None, msg: str = None, **kwargs):
        super(Forward, self).__init__(**kwargs)
        self.to = to
        self.msg = msg


class ForwardSchema(AgentMessageSchema):
    class Meta:
        model_class = Forward

    to = fields.Str(required=True)
    msg = fields.Str(required=True)
