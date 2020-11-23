"""Represents a connection response message."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema

from ..message_types import CONNECTION_RESPONSE, PROTOCOL_PACKAGE
from ..models.connection_detail import ConnectionDetail, ConnectionDetailSchema

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers."
    "connection_response_handler.ConnectionResponseHandler"
)


class ConnectionResponse(AgentMessage):
    """Class representing a connection response."""

    class Meta:
        """Metadata for a connection response."""

        handler_class = HANDLER_CLASS
        schema_class = "ConnectionResponseSchema"
        message_type = CONNECTION_RESPONSE

    # CHANGES 2 BY HARSH MULTANi
    def __init__(self, *, connection: ConnectionDetail = None, my_role: str = None, their_role:str = None, **kwargs):
        """
        Initialize connection response object.

        Args:
            connection: Connection details object

        """
        super().__init__(**kwargs)
        self.connection = connection
        self.my_role = my_role
        self.their_role = their_role


class ConnectionResponseSchema(AgentMessageSchema):
    """Connection response schema class."""

    class Meta:
        """Connection response schema metadata."""

        model_class = ConnectionResponse
        signed_fields = ("connection",)
        unknown = EXCLUDE

    connection = fields.Nested(ConnectionDetailSchema, required=True)

    my_role = fields.Str(
        required=False,
        description="My Role that needs to be passed",
        example="AUTHOR",
    )
    their_role = fields.Str(
        required=False,
        description="Their Role that needs to be passed - useful when opting for auto-accepting connection",
        example="AUTHOR",
    )
