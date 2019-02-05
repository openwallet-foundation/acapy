"""
Represents a connection request message.
"""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ...message_types import MessageTypes
from ...validators import must_not_be_none

from ....models.agent_endpoint import AgentEndpoint, AgentEndpointSchema


class ConnectionRequest(AgentMessage):
    class Meta:
        # handler_class = ConnectionRequestHandler
        schema_class = 'ConnectionRequestSchema'
        message_type = MessageTypes.CONNECTION_REQUEST.value

    def __init__(
            self,
            *,
            endpoint: AgentEndpoint = None,
            did: str = None,
            verkey: str = None,
            **kwargs
        ):
        super(ConnectionRequest, self).__init__(**kwargs)
        self.endpoint = endpoint
        self.did = did
        self.verkey = verkey


class ConnectionRequestSchema(AgentMessageSchema):
    class Meta:
        model_class = ConnectionRequest

    endpoint = fields.Nested(
        AgentEndpointSchema, validate=must_not_be_none, required=True
    )
    did = fields.Str(required=True)
    verkey = fields.Str(required=True)
