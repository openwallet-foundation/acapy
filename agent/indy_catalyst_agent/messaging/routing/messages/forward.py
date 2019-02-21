"""
Forward a message according to registered routing records
"""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import FORWARD

HANDLER_CLASS = "indy_catalyst_agent.messaging.routing.handlers"
".forward_handler.ForwardHandler"


class Forward(AgentMessage):
    """Represents a request to forward a message to a connected agent"""

    class Meta:
        """ """

        handler_class = HANDLER_CLASS
        message_type = FORWARD
        schema_class = "ForwardSchema"

    def __init__(self, *, to: str = None, msg: str = None, **kwargs):
        super(Forward, self).__init__(**kwargs)
        self.to = to
        self.msg = msg


class ForwardSchema(AgentMessageSchema):
    """ """

    class Meta:
        """ """

        model_class = Forward

    to = fields.Str(required=True)
    msg = fields.Str(required=True)
