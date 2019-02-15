"""
Represents an invitation message for establishing connection.
"""

from typing import Sequence
from urllib.parse import parse_qs, urljoin, urlparse

from marshmallow import ValidationError, fields, validates_schema

from ...agent_message import AgentMessage, AgentMessageSchema
from ..message_types import CONNECTION_INVITATION
from ....wallet.util import b64_to_bytes, bytes_to_b64

HANDLER_CLASS = (
    "indy_catalyst_agent.messaging.connections.handlers."
    + "connection_invitation_handler.ConnectionInvitationHandler"
)


class ConnectionInvitation(AgentMessage):
    """Class representing a connection invitation."""

    class Meta:
        handler_class = HANDLER_CLASS
        message_type = CONNECTION_INVITATION
        schema_class = "ConnectionInvitationSchema"

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
        self.recipient_keys = list(recipient_keys) if recipient_keys else []
        self.endpoint = endpoint
        self.routing_keys = list(routing_keys) if routing_keys else []

    def to_url(self) -> str:
        """
        Convert an invitation to URL format for sharing
        """
        c_json = self.to_json()
        c_i = bytes_to_b64(c_json.encode("ascii"), urlsafe=True)
        result = urljoin(self.endpoint, "?c_i={}".format(c_i))
        return result

    @classmethod
    def from_url(cls, url: str) -> "ConnectionInvitation":
        """
        Parse a URL-encoded invitation into a `ConnectionInvitation` message
        """
        parts = urlparse(url)
        query = parse_qs(parts.query)
        if "c_i" in query:
            c_i = b64_to_bytes(query["c_i"][0], urlsafe=True)
            return cls.from_json(c_i)
        return None


class ConnectionInvitationSchema(AgentMessageSchema):
    """Class """

    class Meta:
        model_class = ConnectionInvitation

    label = fields.Str()
    did = fields.Str(required=False)
    recipient_keys = fields.List(fields.Str(), data_key="recipientKeys", required=False)
    endpoint = fields.Str(data_key="serviceEndpoint", required=False)
    routing_keys = fields.List(fields.Str(), data_key="routingKeys", required=False)

    @validates_schema
    def validate_fields(self, data):
        """
        Validate schema fields.
        :param data:
        """
        if data.get("did"):
            if data.get("recipient_keys"):
                raise ValidationError(
                    "Fields are incompatible", ("did", "recipientKeys")
                )
            if data.get("endpoint"):
                raise ValidationError(
                    "Fields are incompatible", ("did", "serviceEndpoint")
                )
        elif not data.get("recipient_keys") or not data.get("endpoint"):
            raise ValidationError(
                "Missing required field(s)", ("did", "recipientKeys", "serviceEndpoint")
            )
