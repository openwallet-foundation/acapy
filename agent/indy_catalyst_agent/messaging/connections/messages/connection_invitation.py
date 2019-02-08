"""
Represents an invitation message for establishing connection.
"""

from marshmallow import (
    ValidationError, fields, validates_schema,
)

from ...agent_message import AgentMessage, AgentMessageSchema, ThreadDecorator
from ...message_types import MessageTypes

from ..handlers.connection_invitation_handler import ConnectionInvitationHandler


class ConnectionInvitation(AgentMessage):
    class Meta:
        handler_class = ConnectionInvitationHandler
        schema_class = 'ConnectionInvitationSchema'
        message_type = MessageTypes.CONNECTION_INVITATION.value

    def __init__(
            self,
            *,
            did: str = None,
            key: str = None,
            endpoint: str = None,
            image_url: str = None,
            label: str = None,
            **kwargs,
        ):
        super(ConnectionInvitation, self).__init__(**kwargs)
        self.did = did
        self.key = key
        self.label = label
        self.endpoint = endpoint
        self.image_url = image_url


class ConnectionInvitationSchema(AgentMessageSchema):
    class Meta:
        model_class = ConnectionInvitation

    label = fields.Str()
    did = fields.Str(required=False)
    key = fields.Str(required=False)
    endpoint = fields.Str(required=False)
    image_url = fields.Str(required=False)

    @validates_schema
    def validate_fields(self, data):
        fields = ()
        if "did" in data:
            if "key" in data:
                raise ValidationError("Fields are incompatible", ("did", "key"))
            if "endpoint" in data:
                raise ValidationError("Fields are incompatible", ("did", "endpoint"))
        elif "key" not in data:
            raise ValidationError("One or the other is required", ("did", "key"))
        elif "endpoint" not in data:
            raise ValidationError("Both fields are required", ("key", "endpoint"))
