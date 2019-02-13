"""
Represents a connection response message
"""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import CONNECTION_RESPONSE
from ....models.connection_detail import ConnectionDetail, ConnectionDetailSchema

HANDLER_CLASS = "indy_catalyst_agent.messaging.connections.handlers.connection_response_handler.ConnectionResponseHandler"


class ConnectionResponse(AgentMessage):
    class Meta:
        handler_class = HANDLER_CLASS
        schema_class = "ConnectionResponseSchema"
        message_type = CONNECTION_RESPONSE

    def __init__(self, *, connection: ConnectionDetail = None, **kwargs):
        super(ConnectionResponse, self).__init__(**kwargs)
        self.connection = connection


class ConnectionResponseSchema(AgentMessageSchema):
    class Meta:
        model_class = ConnectionResponse
        signed_fields = ("connection",)

    connection = fields.Nested(ConnectionDetailSchema, required=True)
