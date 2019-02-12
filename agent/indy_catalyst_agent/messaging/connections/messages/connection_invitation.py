"""
Represents an invitation message for establishing connection.
"""

from typing import Sequence

from marshmallow import (
    ValidationError, fields, validates_schema,
)

from ...agent_message import AgentMessage, AgentMessageSchema
from ..handlers.connection_invitation_handler import ConnectionInvitationHandler
from ..message_types import CONNECTION_INVITATION


class ConnectionInvitation(AgentMessage):
    class Meta:
        handler_class = ConnectionInvitationHandler
        schema_class = 'ConnectionInvitationSchema'
        message_type = CONNECTION_INVITATION

    def __init__(
            self,
            *,
            label: str = None,
            did: str = None,
            recipient_keys: Sequence[str] = None,
            endpoint: str = None,
            routing_keys: Sequence[str] = None,
            **kwargs,
        ):
        super(ConnectionInvitation, self).__init__(**kwargs)
        self.label = label
        self.did = did
        self.recipient_keys = recipient_keys
        self.endpoint = endpoint
        self.routing_keys = routing_keys


class ConnectionInvitationSchema(AgentMessageSchema):
    class Meta:
        model_class = ConnectionInvitation

    label = fields.Str()
    did = fields.Str(required=False)
    recipient_keys = fields.List(fields.Str(), required=False)
    endpoint = fields.Str(data_key="serviceEndpoint", required=False)
    routing_keys = fields.List(fields.Str(), required=False)

    @validates_schema
    def validate_fields(self, data):
        if data.get("did"):
            if data.get("recipient_keys"):
                raise ValidationError("Fields are incompatible", ("did", "recipient_keys"))
            if data.get("serviceEndpoint"):
                raise ValidationError("Fields are incompatible", ("did", "serviceEndpoint"))
        elif not data.get("recipient_keys") or not data.get("serviceEndpoint"):
            raise ValidationError("Missing required field(s)", ("did", "recipient_keys", "serviceEndpoint"))
