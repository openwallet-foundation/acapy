"""
Represents an invitation message for establishing connection.
"""

from marshmallow import Schema, fields, post_load

from ..agent_message import AgentMessage
from ..message_types import MessageTypes
from ..validators import must_not_be_none

from ...models.agent_endpoint import AgentEndpoint, AgentEndpointSchema


class ConnectionInvitation(AgentMessage):
    def __init__(self, endpoint: AgentEndpoint, image_url: str, connection_key: str):
        self.endpoint = endpoint
        self.image_url = image_url
        self.connection_key = connection_key

    @property
    # Avoid clobbering builtin property
    def _type(self) -> str:
        return MessageTypes.CONNECTION_INVITATION.value

    @classmethod
    def deserialize(cls, obj):
        return ConnectionInvitationSchema().load(obj)

    def serialize(self):
        return ConnectionInvitationSchema().dump(self)


class ConnectionInvitationSchema(Schema):
    # Avoid clobbering builtin property
    _type = fields.Str(data_key="@type", required=True)
    endpoint = fields.Nested(
        AgentEndpointSchema, validate=must_not_be_none, required=True
    )
    image_url = fields.Str(required=True)
    connection_key = fields.Str(required=True)

    @post_load
    def make_model(self, data: dict) -> ConnectionInvitation:
        del data["_type"]
        return ConnectionInvitation(**data)
