"""Represents a connection request message."""

from marshmallow import fields

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import CONNECTION_REQUEST
from ..models.connection_detail import ConnectionDetail, ConnectionDetailSchema

HANDLER_CLASS = (
    "aries_cloudagent.messaging.connections.handlers"
    + ".connection_request_handler.ConnectionRequestHandler"
)


class ConnectionRequest(AgentMessage):
    """Class representing a connection request."""

    class Meta:
        """Metadata for a connection request."""

        handler_class = HANDLER_CLASS
        message_type = CONNECTION_REQUEST
        schema_class = "ConnectionRequestSchema"

    def __init__(
        self,
        *,
        connection: ConnectionDetail = None,
        label: str = None,
        image_url: str = None,
        **kwargs
    ):
        """
        Initialize connection request object.

        Args:
            connection (ConnectionDetail): Connection details object
            label: Label for this connection request
        """
        super(ConnectionRequest, self).__init__(**kwargs)
        self.connection = connection
        self.label = label


class ConnectionRequestSchema(AgentMessageSchema):
    """Connection request schema class."""

    class Meta:
        """Connection request schema metadata."""

        model_class = ConnectionRequest

    connection = fields.Nested(ConnectionDetailSchema, required=True)
    label = fields.Str(required=True)
    image_url = fields.Str(data_key="imageUrl", required=False, allow_none=True)
