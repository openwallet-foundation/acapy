"""
Represents a connection response message
"""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ...message_types import MessageTypes
from ...validators import must_not_be_none

from ....models.agent_endpoint import AgentEndpoint, AgentEndpointSchema


class ConnectionResponse(AgentMessage):
    class Meta:
        # handler_class = ConnectionResponseHandler
        schema_class = 'ConnectionResponseSchema'
        message_type = MessageTypes.CONNECTION_RESPONSE.value

    def __init__(self, *, endpoint: AgentEndpoint = None, did: str = None, verkey: str = None, **kwargs):
        super(ConnectionResponse, self).__init__(**kwargs)
        self.endpoint = endpoint
        self.did = did
        self.verkey = verkey


class ConnectionResponseSchema(AgentMessageSchema):
    class Meta:
        model_class = ConnectionResponse

    endpoint = fields.Nested(
        AgentEndpointSchema, validate=must_not_be_none, required=True
    )
    did = fields.Str(required=True)
    verkey = fields.Str(required=True)
