"""
Represents a connection response message
"""

from marshmallow import Schema, fields, post_load

from ...agent_message import AgentMessage
from ...message_types import MessageTypes
from ...validators import must_not_be_none

from ....models.agent_endpoint import AgentEndpoint, AgentEndpointSchema


class ConnectionResponse(AgentMessage):
    def __init__(self, endpoint: AgentEndpoint, did: str, verkey: str):
        self.endpoint = endpoint
        self.did = did
        self.verkey = verkey

    @property
    # Avoid clobbering builtin property
    def _type(self):
        return MessageTypes.CONNECTION_RESPONSE.value

    @classmethod
    def deserialize(cls, obj):
        return ConnectionResponseSchema().load(obj)

    def serialize(self):
        return ConnectionResponseSchema().dump(self)


class ConnectionResponseSchema(Schema):
    # Avoid clobbering builtin property
    _type = fields.Str(data_key="@type", required=True)
    endpoint = fields.Nested(
        AgentEndpointSchema, validate=must_not_be_none, required=True
    )
    did = fields.Str(required=True)
    verkey = fields.Str(required=True)

    @post_load
    def make_model(self, data: dict) -> ConnectionResponse:
        del data["_type"]
        return ConnectionResponse(**data)
