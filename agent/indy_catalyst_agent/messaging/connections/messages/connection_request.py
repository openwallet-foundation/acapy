"""
Represents a connection request message.
"""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import CONNECTION_REQUEST
from ..models.connection_detail import ConnectionDetail, ConnectionDetailSchema

HANDLER_CLASS = (
    "indy_catalyst_agent.messaging.connections.handlers"
    + ".connection_request_handler.ConnectionRequestHandler"
)


class ConnectionRequest(AgentMessage):
    """ """

    class Meta:
        """ """

        handler_class = HANDLER_CLASS
        message_type = CONNECTION_REQUEST
        schema_class = "ConnectionRequestSchema"

    def __init__(
        self, *, connection: ConnectionDetail = None, label: str = None, **kwargs
    ):
        super(ConnectionRequest, self).__init__(**kwargs)
        self.connection = connection
        self.label = label


class ConnectionRequestSchema(AgentMessageSchema):
    """ """

    class Meta:
        """ """

        model_class = ConnectionRequest

    connection = fields.Nested(ConnectionDetailSchema, required=True)
    label = fields.Str(required=True)
