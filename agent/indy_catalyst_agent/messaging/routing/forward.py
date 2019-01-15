"""
Represents a forward message.
"""

from marshmallow import Schema, fields, post_load

from ..agent_message import AgentMessage
from ..message_types import MessageTypes


class Forward(AgentMessage):
    def __init__(self, to: str, msg: str):
        self.to = to
        self.msg = msg

    @property
    # Avoid clobbering builtin property
    def _type(self):
        return MessageTypes.FORWARD.value

    @classmethod
    def deserialize(cls, obj):
        return ForwardSchema().load(obj)

    def serialize(self):
        return ForwardSchema().dump(self)


class ForwardSchema(Schema):
    # Avoid clobbering builtin property
    _type = fields.Str(data_key="@type", required=True)
    to = fields.Str(required=True)
    msg = fields.Str(required=True)

    @post_load
    def make_model(self, data: dict) -> Forward:
        del data["_type"]
        return Forward(**data)
